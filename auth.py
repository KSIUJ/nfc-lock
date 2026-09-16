import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from time import time

import requests

from logger import Logger

import config.main as config
import config.erc_secret as erc_secret

log = Logger().getLog()

REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_GRANT_CACHE_SECONDS = 60 * 60 * 24
EVENT_BATCH_SIZE = 200


class AuthResult:
    TYPE_NORMAL = 1
    # Decided locally from the on-disk card cache because ERC was unreachable.
    TYPE_OFFLINE = 2

    def __init__(self, is_granted, type, reason=None):
        self.isGranted = is_granted
        self.type = type
        self.reason = reason


_lock = threading.RLock()
# Authoritative list mirrored from ERC (/api/lock/uids). Refreshed wholesale
# on a schedule owned by the application - entries don't expire on their own,
# they're only ever replaced by the next refresh.
_uid_set: set[str] = set()
_uid_etag: str | None = None
# Fallback list mirrored from ERC (/api/lock/cards), used only while ERC is
# unreachable. Same "never expires on its own" rule as _uid_set.
_cards: dict[str, dict] = {}
# UIDs granted by a live /api/lock/check call that aren't (yet) in _uid_set.
# Unlike _uid_set/_cards, these entries DO expire, after erc['grant_cache_seconds'].
_grant_cache: dict[str, float] = {}
_queue: list[dict] = []


def _base_url() -> str:
    return config.erc["base_url"].rstrip("/")


def _headers() -> dict:
    return {"Authorization": f"Bearer {erc_secret.api_key}"}


def _client_cert() -> tuple[str, str]:
    return (config.erc["client_cert_file"], config.erc["client_key_file"])


def _cards_file() -> str:
    return config.erc["cards_cache_file"]


def _queue_file() -> str:
    return config.erc["queue_file"]


def _atomic_write(path: str, data):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


def _load_cards_from_disk():
    global _cards
    try:
        with open(_cards_file()) as f:
            body = json.load(f)
        _cards = {c["uid"]: c for c in body.get("cards", [])}
        log.info(f"Loaded {len(_cards)} card(s) from disk cache")
    except FileNotFoundError:
        log.warning("No disk card cache found yet - offline fallback will deny everyone until ERC is reachable")
    except Exception as e:
        log.error(f"Failed to load disk card cache: {e}")


def _load_queue_from_disk():
    global _queue
    try:
        with open(_queue_file()) as f:
            _queue = json.load(f)
        log.info(f"Loaded {len(_queue)} queued event(s) from disk")
    except FileNotFoundError:
        _queue = []
    except Exception as e:
        log.error(f"Failed to load event queue: {e}")
        _queue = []


def _save_queue_to_disk():
    try:
        _atomic_write(_queue_file(), _queue)
    except Exception as e:
        log.error(f"Failed to persist event queue: {e}")


def refresh_uids():
    global _uid_set, _uid_etag
    headers = _headers()
    if _uid_etag:
        headers["If-None-Match"] = _uid_etag
    try:
        resp = requests.get(
            f"{_base_url()}/api/lock/uids", headers=headers, cert=_client_cert(), timeout=REQUEST_TIMEOUT_SECONDS
        )
        if resp.status_code == 304:
            log.debug("UID list unchanged since last refresh")
            return
        resp.raise_for_status()
        body = resp.json()
        with _lock:
            _uid_set = set(body["uids"])
            _uid_etag = resp.headers.get("ETag") or f'"{body.get("version")}"'
        log.info(f"Refreshed in-memory UID list from ERC ({len(_uid_set)} card(s))")
    except Exception as e:
        log.error(f"Failed to refresh UID list from ERC: {e}")


def refresh_cards():
    global _cards
    try:
        resp = requests.get(
            f"{_base_url()}/api/lock/cards",
            headers=_headers(),
            cert=_client_cert(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        body = resp.json()
        with _lock:
            _cards = {c["uid"]: c for c in body.get("cards", [])}
        _atomic_write(_cards_file(), body)
        log.info(f"Refreshed disk card cache from ERC ({len(_cards)} card(s))")
    except Exception as e:
        log.error(f"Failed to refresh disk card cache from ERC: {e}")


def queue_event(uid: str, result: str, reason: str = None, at: str = None):
    """Reports one event to ERC. Tries to send it directly first so the log stays
    close to real-time; only falls back to the persisted queue (retried every
    few seconds by the application, see app.py) if ERC can't be reached right now."""
    event = {"uid": uid, "result": result, "device": config.erc.get("device")}
    if reason:
        event["reason"] = reason[:200]
    event["at"] = at or datetime.now(timezone.utc).isoformat()

    status = _post_events([event])
    if status == "ok":
        return
    if status == "rejected":
        log.error(f"ERC rejected event, dropping: {event}")
        return

    log.warning(f"ERC unreachable, queuing event for retry: {event}")
    with _lock:
        _queue.append(event)
        _save_queue_to_disk()


def _post_events(events: list) -> str:
    """Returns 'ok' (201), 'rejected' (4xx) or 'unavailable' (network error / non-2xx/4xx)."""
    try:
        resp = requests.post(
            f"{_base_url()}/api/lock/events",
            headers=_headers(),
            json=events,
            cert=_client_cert(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as e:
        log.error(f"Failed to reach ERC event endpoint: {e}")
        return "unavailable"
    if resp.status_code == 201:
        return "ok"
    if 400 <= resp.status_code < 500:
        log.error(f"ERC rejected event batch ({resp.status_code}): {resp.text}")
        return "rejected"
    log.error(f"ERC event upload failed ({resp.status_code})")
    return "unavailable"


def _drop_from_queue(n: int):
    with _lock:
        del _queue[:n]
        _save_queue_to_disk()


def flush_queue():
    with _lock:
        if not _queue:
            return
        batch = list(_queue[:EVENT_BATCH_SIZE])

    status = _post_events(batch)
    if status == "unavailable":
        return
    if status == "ok":
        _drop_from_queue(len(batch))
        log.info(f"Flushed {len(batch)} queued event(s) to ERC")
        return

    # A batch rejection means at least one event in it is malformed. Retry
    # one at a time so a single bad event doesn't block the rest of the queue.
    processed = 0
    for event in batch:
        single_status = _post_events([event])
        if single_status == "unavailable":
            break
        if single_status == "rejected":
            log.error(f"Dropping malformed queued event: {event}")
        processed += 1
    _drop_from_queue(processed)


def check(uid: str):
    """POSTs /api/lock/check. Returns the response body, or None if ERC/Keycloak is unreachable."""
    try:
        resp = requests.post(
            f"{_base_url()}/api/lock/check",
            headers=_headers(),
            # log=False: every decision is reported through queue_event()/flush_queue()
            # regardless of where it came from, so ERC doesn't need to log this itself
            # too (that would double the entry in ERC's log).
            json={"uid": uid, "device": config.erc.get("device"), "log": False},
            cert=_client_cert(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as e:
        log.error(f"ERC check request failed: {e}")
        return None

    if resp.status_code == 503:
        log.warning("ERC reports Keycloak is unreachable")
        return None
    resp.raise_for_status()
    return resp.json()


def clear_cache():
    """Forces every not-yet-expired /check grant to be re-verified with ERC,
    and pulls a fresh copy of both lists right away. _uid_set and _cards are
    left alone - they're only ever replaced wholesale by a refresh, not
    invalidated by this."""
    with _lock:
        _grant_cache.clear()
    log.info("Grant cache cleared; forcing UID/card refresh from ERC")
    refresh_uids()
    refresh_cards()


def load():
    """Loads on-disk state (card fallback list, pending event queue). Call once at startup,
    before the first sync()."""
    _load_cards_from_disk()
    _load_queue_from_disk()


def sync():
    """Refreshes both card lists from ERC and flushes any queued events.
    Called once at startup and then periodically by the application (see app.py) -
    this module does not schedule its own refreshes."""
    refresh_uids()
    refresh_cards()
    flush_queue()


def _grant_cache_seconds() -> float:
    return config.erc.get("grant_cache_seconds", DEFAULT_GRANT_CACHE_SECONDS)


def authenticate(uid: str) -> AuthResult:
    if getattr(config, "bypass", False):
        log.warning(f"BYPASS mode enabled - granting access unconditionally: {uid}")
        queue_event(uid, "granted", "tryb bypass włączony")
        return AuthResult(True, AuthResult.TYPE_NORMAL, "tryb bypass włączony")

    with _lock:
        in_official_list = uid in _uid_set
        grant_cache_hit = uid in _grant_cache and time() - _grant_cache[uid] < _grant_cache_seconds()

    if in_official_list or grant_cache_hit:
        reason = (
            "z listy w pamięci (/api/lock/uids)"
            if in_official_list
            else "z pamięci podręcznej zamka (ostatnio potwierdzone przez /api/lock/check)"
        )
        log.debug(f"UID granted from local cache: {reason}")
        queue_event(uid, "granted", reason)
        return AuthResult(True, AuthResult.TYPE_NORMAL, reason)

    # Not confirmed as granted (or the grant cache entry expired): never deny
    # without asking ERC first.
    try:
        body = check(uid)
    except Exception as e:
        log.error(f"ERC check failed: {e}")
        reason = f"błąd konfiguracji ERC ({e})"
        queue_event(uid, "error", reason)
        return AuthResult(False, AuthResult.TYPE_NORMAL, reason)

    if body is not None:
        granted = body["granted"]
        reason = body.get("reason") or ("dostęp przyznany" if granted else "dostęp odmówiony")
        if granted:
            with _lock:
                _grant_cache[uid] = time()
        queue_event(uid, "granted" if granted else "denied", reason)
        return AuthResult(granted, AuthResult.TYPE_NORMAL, reason)

    # ERC couldn't reach Keycloak (503) or ERC itself is unreachable: fall
    # back to the last card list persisted to disk and report the decision
    # once a connection is available again.
    with _lock:
        card = _cards.get(uid)
    granted = card is not None
    reason = f"decyzja offline z kopii na dysku: {'karta ' + card['name'] if card else 'karta nieznana'}"
    log.warning(f"ERC unavailable, deciding offline for {uid}: {reason}")
    queue_event(uid, "granted" if granted else "denied", reason)
    return AuthResult(granted, AuthResult.TYPE_OFFLINE, reason)
