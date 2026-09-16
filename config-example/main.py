# Path to NFC reader USB device
nfc_reader = {
    'input_device': '/dev/input/by-id/usb-IC_Reader_IC_Reader_08FF20171101-event-kbd'
}

# GPIO mappings for info LEDs. Skip if no LEDs were attached.
led = {
    'green_gpio': 7,
    'green_reversed': False,
    'red_gpio': 11,
    'red_reversed': False
}

# Lock configuration
lock = {
    'lock_gpio': 40,
    'opening_time': 5,
    'lock_reversed': True
}

# If True, every card is accepted without checking ERC or the disk cache.
# Dangerous - only for testing/maintenance, never leave enabled in production.
bypass = False

# ERC connection settings (non-secret). The API key lives in erc_secret.py
# since config-example/ is committed to git. ERC's origin also requires this
# client to present an mTLS certificate during the TLS handshake.
erc = {
    'base_url': 'https://erc.ksi.sh',
    # Reader name reported alongside checks/events, shown in ERC's log.
    'device': 'drzwi-siedziba',
    # Full card list, refreshed hourly, used to decide access while ERC is
    # unreachable (e.g. right after a restart with an empty in-memory cache).
    'cards_cache_file': '/opt/nfc-lock/cache/cards.json',
    # Events that couldn't be reported to ERC yet, persisted so they survive
    # a restart and get retried on the next successful connection.
    'queue_file': '/opt/nfc-lock/cache/events_queue.json',
    'client_cert_file': '/opt/nfc-lock/cert/erc-client.crt',
    'client_key_file': '/opt/nfc-lock/cert/erc-client.key',
    # How long a card granted by /api/lock/check (but not yet part of the
    # official /api/lock/uids list) stays valid in the lock's own cache
    # before it must be re-checked with ERC. The official list itself never
    # expires this way - it's only ever replaced wholesale by the next
    # hourly refresh.
    'grant_cache_seconds': 60 * 60 * 24,
}
