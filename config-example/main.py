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
    'base_url': 'https://erc.internal.ksi.sh',
    # Reader name reported alongside checks/events, shown in ERC's log.
    'device': 'drzwi-siedziba',
    # Normal card list (GET /api/lock/uids), refreshed hourly. Valid for
    # ttlSeconds (48h by default) since it was last confirmed by ERC - past
    # that, without a successful refresh, it stops granting access.
    'normal_uids_cache_file': '/opt/nfc-lock/cache/uids.json',
    # Permanent card list (GET /api/lock/uids/permanent) - never expires, so
    # it's what decides access while ERC is unreachable (e.g. right after a
    # restart, or once the normal list above has expired).
    'permanent_uids_cache_file': '/opt/nfc-lock/cache/uids_permanent.json',
    # Events that couldn't be reported to ERC yet, persisted so they survive
    # a restart and get retried on the next successful connection.
    'queue_file': '/opt/nfc-lock/cache/events_queue.json',
    'client_cert_file': '/opt/nfc-lock/cert/erc-client.crt',
    'client_key_file': '/opt/nfc-lock/cert/erc-client.key',
    # How long a card granted by /api/lock/check (but not yet part of either
    # UID list) stays valid in the lock's own cache before it must be
    # re-checked with ERC. Every successful refresh of the normal list also
    # drops cached grants ERC no longer lists, so a revoked card stops working
    # within one refresh interval (1h) either way. The two lists themselves
    # never expire this way - each is only ever replaced wholesale by its
    # next refresh.
    'grant_cache_seconds': 60 * 60,
}
