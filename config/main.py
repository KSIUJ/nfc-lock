nfc_reader = {
    'input_device': '/dev/input/by-id/usb-IC_Reader_IC_Reader_08FF20171101-event-kbd'
}

led = {
    'green_gpio': 7,
    'green_reversed': False,
    'red_gpio': 11,
    'red_reversed': False
}

lock = {
    'lock_gpio': 40,
    'opening_time': 5,
    'lock_reversed': True
}

server = {
    'port': 1234,
    'cert_file': '/opt/nfc-lock/cert/lock.crt',
    'key_file': '/opt/nfc-lock/cert/lock.key'
}

erc = {
    'endpoint': 'https://ercendpoint.com'
}

hardcoded_uid = [
    "12345678",
    "90abcdef"
]