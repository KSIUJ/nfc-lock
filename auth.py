import requests
from time import time
from logger import Logger

import config.main as config
import config.keycloak_secret as keycloak_secret

log = Logger().getLog()
cache : dict[str, float] = {}
CACHE_EXPIRE_TIME_SECONDS = 60 * 60 * 24 * 7 * 2
REQUEST_TIMEOUT_SECONDS = 10

_token = None
_token_expiry = 0.0
_group_id = None


class AuthResult:
    TYPE_NORMAL = 1
    TYPE_HARDCODED = 2

    def __init__(self, is_granted, type, reason=None):
        self.isGranted = is_granted
        self.type = type
        self.reason = reason


def _realm_url(path: str) -> str:
    return f"{config.keycloak['server_url']}/admin/realms/{config.keycloak['realm']}{path}"


def _client_cert() -> tuple[str, str]:
    return (config.keycloak['client_cert_file'], config.keycloak['client_key_file'])


def _get_token() -> str:
    global _token, _token_expiry
    if _token is not None and time() < _token_expiry:
        return _token

    resp = requests.post(
        f"{config.keycloak['server_url']}/realms/{config.keycloak['realm']}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": keycloak_secret.client_id,
            "client_secret": keycloak_secret.client_secret,
        },
        cert=_client_cert(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    body = resp.json()
    _token = body["access_token"]
    _token_expiry = time() + body["expires_in"] - 10
    return _token


def _get_group_id(token: str) -> str:
    global _group_id
    if _group_id is not None:
        return _group_id

    resp = requests.get(
        _realm_url("/groups"),
        headers={"Authorization": f"Bearer {token}"},
        params={"search": config.keycloak["required_group"], "exact": "true"},
        cert=_client_cert(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    groups = resp.json()
    if not groups:
        raise Exception(f"Keycloak group '{config.keycloak['required_group']}' not found")
    _group_id = groups[0]["id"]
    return _group_id


def _user_has_access(uid: str) -> tuple[bool, str]:
    token = _get_token()
    group_id = _get_group_id(token)

    resp = requests.get(
        _realm_url(f"/groups/{group_id}/members"),
        headers={"Authorization": f"Bearer {token}"},
        params={"briefRepresentation": "false"},
        cert=_client_cert(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    members = resp.json()

    attribute = config.keycloak["nfc_attribute"]
    required_group = config.keycloak["required_group"]
    for member in members:
        if not member.get("enabled", True):
            continue
        values = member.get("attributes", {}).get(attribute, [])
        if uid in values:
            return True, f"matched user '{member.get('username')}' in group '{required_group}'"
    return False, f"no enabled member of group '{required_group}' has nfc_uid '{uid}'"


def authenticate(uid: str):
    if getattr(config, "bypass", False):
        log.warning(f"BYPASS mode enabled - granting access unconditionally: {uid}")
        return AuthResult(True, AuthResult.TYPE_NORMAL, "BYPASS mode enabled")

    if uid in cache:
        if time() - cache[uid] < CACHE_EXPIRE_TIME_SECONDS:
            log.debug("ID in cache")
            return AuthResult(True, AuthResult.TYPE_NORMAL, "cached")
        else:
            cache.pop(uid)

    try:
        log.debug("Making request to Keycloak")
        granted, reason = _user_has_access(uid)
        log.debug(f"Access granted: {granted} ({reason})")
        if granted:
            cache[uid] = time()
        return AuthResult(granted, AuthResult.TYPE_NORMAL, reason)
    except Exception as e:
        log.error(str(e))
        reason = f"Keycloak unreachable ({e}), falling back to hardcoded IDs"
        return AuthResult(uid in config.hardcoded_uid, AuthResult.TYPE_HARDCODED, reason)
