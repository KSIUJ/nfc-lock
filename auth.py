import requests
from time import time
from logger import Logger

import config.main as config
import config.erc_secret as erc_secret

log = Logger().getLog()
cache : dict[str, float] = {}
CACHE_EXPIRE_TIME_SECONDS = 60 * 60 * 24 * 7 * 2


class AuthResult:
    TYPE_NORMAL = 1
    TYPE_HARDCODED = 2

    def __init__(self, is_granted, type):
        self.isGranted = is_granted
        self.type = type


def authenticate(uid: str):
    if uid in cache:
        if time() - cache[uid] < CACHE_EXPIRE_TIME_SECONDS:
            log.debug("ID in cache")
            return AuthResult(True, AuthResult.TYPE_NORMAL)
        else:
            cache.pop(uid)

    try:
        log.debug("Making request to auth server")
        x = requests.post(
            config.erc["endpoint"],
            json={
                "client_id": erc_secret.client_id,
                "client_secret": erc_secret.client_secret,
                "card_id": uid,
            },
            timeout=2,
        )
        log.debug(f"Returned status code: {x.status_code}")
        if x.status_code == 200:
            cache[uid] = time()
        return AuthResult(x.status_code == 200, AuthResult.TYPE_NORMAL)
    except Exception as e:
        log.error(str(e))
        return AuthResult(uid in config.hardcoded_uid, AuthResult.TYPE_HARDCODED)
