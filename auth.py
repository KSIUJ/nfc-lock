import urllib.request as url
import urllib.error

ERC_ENDPOINT = "ENDPOINT"


def authenticate(card_uid: str):
    try:
        with url.urlopen(ERC_ENDPOINT + card_uid) as response:
            return response.getcode() == 200
    except urllib.error.HTTPError:
        return False
