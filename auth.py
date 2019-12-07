import requests
from logger import Logger

import config.main as config
import config.erc_secret as erc_secret

log = Logger().getLog()

class AuthResult:
    TYPE_NORMAL = 1
    TYPE_HARDCODED = 2

    def __init__(self, is_granted, type):
        self.isGranted = is_granted
        self.type = type


def authenticate(uid: str):
    try:
        log.debug('Making request to auth server')
        x = requests.post(config.erc['endpoint'], json={'client_id': erc_secret.client_id, 'client_secret': erc_secret.client_secret, 'card_id': uid}, timeout=2)
        log.debug('Returned status code: '+str(x.status_code))
        return AuthResult(x.status_code == 200, AuthResult.TYPE_NORMAL)
    except Exception as e:
        log.error(str(e))
        return AuthResult(uid in config.hardcoded_uid, AuthResult.TYPE_HARDCODED)
