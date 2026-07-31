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

# Configuration for a server that allows to remotely open the door
server = {
    'port': 1234,
    'cert_file': '/opt/nfc-lock/cert/lock.crt',
    'key_file': '/opt/nfc-lock/cert/lock.key'
}

# If True, every card is accepted without checking Keycloak or hardcoded_uid.
# Dangerous - only for testing/maintenance, never leave enabled in production.
bypass = False

# Keycloak connection settings (non-secret). Client id/secret live in
# keycloak_secret.py since config-example/ is committed to git.
keycloak = {
    'server_url': 'https://auth.internal.ksi.sh',
    'realm': 'ksi',
    'nfc_attribute': 'nfc_uid',
    'required_group': 'door-access'
}

# IDs of cards that can open the door when Keycloak is not available
hardcoded_uid = [
    "12345678",
    "90abcdef"
]
