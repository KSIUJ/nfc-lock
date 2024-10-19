# Path to NFC reader USB device
nfc_reader = {
    "input_device": "/dev/input/by-id/usb-IC_Reader_IC_Reader_08FF20171101-event-kbd"
}

# GPIO mappings for info LEDs. Skip if no LEDs were attached.
led = {
    "green_gpio": 7,
    "green_reversed": False,
    "red_gpio": 11,
    "red_reversed": False,
}

# Lock configuration
lock = {
    "lock_gpio": 40,
    "opening_time": 5,
    "lock_reversed": True,
}

# Configuration for a server that allows to remotely open the door
server = {
    "port": 1234,
    "cert_file": "/opt/nfc-lock/cert/lock.crt",
    "key_file": "/opt/nfc-lock/cert/lock.key",
}

# ERC server endpoint
erc = {
    "endpoint": "https://ercendpoint.com",
    "bulk-endpoint": "https://ercendpoint.com/bulk",
}

# Cache configration
cache = {
    "refresh": 60 * 60 * 24,
    "retry": 60 * 60,
    "lazy": False,
}

# IDs of cards that can open the door when ERC is not available
hardcoded_uid = ["12345678", "90abcdef"]
