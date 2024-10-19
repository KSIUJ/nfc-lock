import requests
from time import time
from logger import Logger
import json

import config.main as config
import config.erc_secret as erc_secret

log = Logger().getLog()
cache: set[str] = set()

last_cache_hit = 0
last_cache_try = 0

CACHE_REFRESH_WINDOW_SECONDS = config.cache["refresh"] or 60 * 60
CACHE_RETRY_WINDOW_SECONDS = config.cache["refresh"] or 60 * 5
CACHE_IS_LAZY = config.cache["lazy"] or False


class AuthResult:
    TYPE_NORMAL = 1
    TYPE_HARDCODED = 2

    def __init__(self, is_granted, type):
        self.isGranted = is_granted
        self.type = type


def refresh_cache():
    global cache
    log.debug("Making bulk request to auth server")
    x = requests.post(
        config.erc["bulk-endpoint"],
        json={
            "client_id": erc_secret.client_id,
            "client_secret": erc_secret.client_secret,
        },
        timeout=2,
    )
    log.debug(f"Returned status code: {x.status_code}")
    cache = set(json.dumps(x))


def authenticate(uid: str):
    global last_cache_hit, last_cache_try
    now = time()
    if now - last_cache_hit > CACHE_REFRESH_WINDOW_SECONDS:
        if now - last_cache_try > CACHE_RETRY_WINDOW_SECONDS:
            try:
                refresh_cache()
                last_cache_hit = now
            except Exception as e:
                log.error(str(e))
            finally:
                last_cache_try = now

    if uid in config.hardcoded_uid:
        return AuthResult(True, AuthResult.TYPE_HARDCODED)
    elif uid in cache:
        log.debug("ID in cache")
        return AuthResult(True, AuthResult.TYPE_NORMAL)
    elif not CACHE_IS_LAZY:
        return authenticate_single(uid)
    else:
        return AuthResult(False, AuthResult.TYPE_NORMAL)


def authenticate_single(uid: str):
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
        return AuthResult(x.status_code == 200, AuthResult.TYPE_NORMAL)
    except Exception as e:
        log.error(str(e))
        return AuthResult(False, AuthResult.TYPE_NORMAL)
