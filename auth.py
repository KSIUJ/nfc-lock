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
DEFAULT_GRANT_CACHE_SECONDS = 60 * 60
# Fallback if a stored normal-list body somehow has no ttlSeconds (fresh install
# with a hand-written cache file, say). ERC's own default is the same 48h.
DEFAULT_NORMAL_LIST_TTL_SECONDS = 60 * 60 * 48
EVENT_BATCH_SIZE = 200

# Canonical `reason` strings for events the lock decided on its own, per ERC's
# lock-api.md "Nazewnictwo powodów" - these land straight in the ERC panel.
REASON_CACHE = "cache zamka"
REASON_OFFLINE = "offline: z lokalnej kopii"


class AuthResult:
    TYPE_NORMAL = 1
    # Decided locally from the permanent list because ERC was unreachable.
    TYPE_OFFLINE = 2

    def __init__(self, is_granted, type, reason=None):
        self.isGranted = is_granted
        self.type = type
        self.reason = reason


_lock = threading.RLock()

# Normal list (GET /api/lock/uids): valid for ttlSeconds (48h by default)
# after generatedAt, renewed by every successful refresh *and* every 304.
# Once it expires without a successful refresh, it stops granting access -
# see _normal_list_valid().
_normal_uids: set[str] = set()
_normal_etag: str | None = None
_normal_last_body: dict | None = None  # raw body as last received/renewed, incl. expiresAt

# Permanent list (GET /api/lock/uids/permanent): no expiry. Only ever
# replaced wholesale by a successful refresh - this is the offline fallback,
# equivalent to the old hand-maintained hardcoded_uid list.
_permanent_uids: set[str] = set()
_permanent_etag: str | None = None

# UIDs granted by a live /api/lock/check call that aren't on either list
# above (yet). Unlike the two lists, these entries DO expire, after
# erc['grant_cache_seconds'] - and every successful refresh of the normal list
# drops the ones ERC no longer lists (see _prune_grant_cache), so a revoked
# card stops opening the door within one refresh interval.
_grant_cache: dict[str, float] = {}

_queue: list[dict] = []


def _base_url() -> str:
    return config.erc["base_url"].rstrip("/")


def _headers() -> dict:
    return {"Authorization": f"Bearer {erc_secret.api_key}"}


def _client_cert() -> tuple[str, str]:
    return (config.erc["client_cert_file"], config.erc["client_key_file"])


def _normal_uids_file() -> str:
    return config.erc["normal_uids_cache_file"]


def _permanent_uids_file() -> str:
    return config.erc["permanent_uids_cache_file"]


def _queue_file() -> str:
    return config.erc["queue_file"]


def _parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


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


def _load_normal_list_from_disk():
    global _normal_uids, _normal_etag, _normal_last_body
    try:
        with open(_normal_uids_file()) as f:
            body = json.load(f)
        _normal_uids = set(body["uids"])
        _normal_etag = f'"{body["version"]}"'
        _normal_last_body = body
        log.info(f"Loaded {len(_normal_uids)} UID(s) from disk (normal list, valid until {body.get('expiresAt')})")
    except FileNotFoundError:
        log.warning("No disk copy of the normal UID list yet")
    except Exception as e:
        log.error(f"Failed to load normal UID list from disk: {e}")


def _load_permanent_list_from_disk():
    global _permanent_uids, _permanent_etag
    try:
        with open(_permanent_uids_file()) as f:
            body = json.load(f)
        _permanent_uids = set(body["uids"])
        _permanent_etag = f'"{body["version"]}"'
        log.info(f"Loaded {len(_permanent_uids)} UID(s) from disk (permanent list)")
    except FileNotFoundError:
        log.warning("No disk copy of the permanent UID list yet - offline fallback will deny everyone")
    except Exception as e:
        log.error(f"Failed to load permanent UID list from disk: {e}")


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


def _normal_list_valid() -> bool:
    with _lock:
        body = _normal_last_body
    if body is None or "expiresAt" not in body:
        return False
    try:
        return time() < _parse_iso(body["expiresAt"])
    except Exception:
        return False


def _prune_grant_cache():
    """Drops /check grants for cards ERC's freshly confirmed normal list no
    longer has. ERC builds that list from the same rule /check uses, so a
    card missing from it has been revoked (or never made it, and the next
    swipe simply asks ERC again). Call with _lock held."""
    revoked = [uid for uid in _grant_cache if uid not in _normal_uids]
    for uid in revoked:
        del _grant_cache[uid]
    if revoked:
        log.info(f"Dropped {len(revoked)} cached grant(s) no longer on ERC's list")


def refresh_normal_uids():
    global _normal_uids, _normal_etag, _normal_last_body
    headers = _headers()
    if _normal_etag:
        headers["If-None-Match"] = _normal_etag
    try:
        resp = requests.get(
            f"{_base_url()}/api/lock/uids", headers=headers, cert=_client_cert(), timeout=REQUEST_TIMEOUT_SECONDS
        )
        if resp.status_code == 304:
            # Still current: ERC confirms the list is unchanged, which counts
            # the same as a fresh fetch - renew validity for another full TTL.
            with _lock:
                if _normal_last_body is not None:
                    ttl = _normal_last_body.get("ttlSeconds", DEFAULT_NORMAL_LIST_TTL_SECONDS)
                    _normal_last_body["expiresAt"] = datetime.fromtimestamp(
                        time() + ttl, tz=timezone.utc
                    ).isoformat()
                    _atomic_write(_normal_uids_file(), _normal_last_body)
                _prune_grant_cache()
            log.debug("Normal UID list unchanged, validity renewed")
            return
        resp.raise_for_status()
        body = resp.json()
        with _lock:
            _normal_uids = set(body["uids"])
            _normal_etag = resp.headers.get("ETag") or f'"{body.get("version")}"'
            _normal_last_body = body
            _atomic_write(_normal_uids_file(), body)
            _prune_grant_cache()
        log.info(f"Refreshed normal UID list from ERC ({len(_normal_uids)} card(s), valid until {body.get('expiresAt')})")
    except Exception as e:
        log.error(f"Failed to refresh normal UID list from ERC: {e}")


def refresh_permanent_uids():
    global _permanent_uids, _permanent_etag
    headers = _headers()
    if _permanent_etag:
        headers["If-None-Match"] = _permanent_etag
    try:
        resp = requests.get(
            f"{_base_url()}/api/lock/uids/permanent",
            headers=headers,
            cert=_client_cert(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if resp.status_code == 304:
            log.debug("Permanent UID list unchanged")
            return
        resp.raise_for_status()
        body = resp.json()
        with _lock:
            _permanent_uids = set(body["uids"])
            _permanent_etag = resp.headers.get("ETag") or f'"{body.get("version")}"'
            _atomic_write(_permanent_uids_file(), body)
        log.info(f"Refreshed permanent UID list from ERC ({len(_permanent_uids)} card(s))")
    except Exception as e:
        log.error(f"Failed to refresh permanent UID list from ERC: {e}")


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


def load():
    """Loads on-disk state (both UID lists, pending event queue). Call once at
    startup, before the first sync()."""
    _load_normal_list_from_disk()
    _load_permanent_list_from_disk()
    _load_queue_from_disk()


def sync():
    """Refreshes both UID lists from ERC and flushes any queued events.
    Called once at startup and then periodically by the application (see app.py) -
    this module does not schedule its own refreshes."""
    refresh_normal_uids()
    refresh_permanent_uids()
    flush_queue()


def _grant_cache_seconds() -> float:
    return config.erc.get("grant_cache_seconds", DEFAULT_GRANT_CACHE_SECONDS)


def authenticate(uid: str) -> AuthResult:
    if getattr(config, "bypass", False):
        log.warning(f"BYPASS mode enabled - granting access unconditionally: {uid}")
        queue_event(uid, "granted", "tryb bypass włączony")
        return AuthResult(True, AuthResult.TYPE_NORMAL, "tryb bypass włączony")

    with _lock:
        on_permanent_list = uid in _permanent_uids
        on_normal_list = uid in _normal_uids
        grant_cache_hit = uid in _grant_cache and time() - _grant_cache[uid] < _grant_cache_seconds()

    # The permanent list always grants. The normal list only grants while
    # it's still within its TTL - past that it's treated as absent, same as
    # any other unknown card.
    if on_permanent_list or (on_normal_list and _normal_list_valid()) or grant_cache_hit:
        log.debug(f"UID granted from local cache for {uid}")
        queue_event(uid, "granted", REASON_CACHE)
        return AuthResult(True, AuthResult.TYPE_NORMAL, REASON_CACHE)

    # Nothing confirms a grant locally: never deny without asking ERC first.
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

    # ERC couldn't reach Keycloak (503) or ERC itself is unreachable: the only
    # thing we can still trust offline is the permanent list (the normal list
    # would already have granted above if it were still valid).
    granted = on_permanent_list
    log.warning(f"ERC unavailable, deciding offline for {uid}: granted={granted}")
    queue_event(uid, "granted" if granted else "denied", REASON_OFFLINE)
    return AuthResult(granted, AuthResult.TYPE_OFFLINE, REASON_OFFLINE)
