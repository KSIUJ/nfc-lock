from auth import authenticate, AuthResult
from reader import NFCReader
from gpio import Outputs, LEDs
from time import sleep
from server import Server
from logger import Logger

import config.main as config
import config.server_secret as server_secret

import struct

server = Server()

log = Logger().getLog()

with Outputs() as out:
    server.start(password=server_secret.password, openingLock=out.open_door, port=8000)
    log.info('Starting main loop')
    out.control_led(LEDs.RED_GREEN_DIMM_IN_OUT_TOGETHER, frequency=0.2, number_of_blinks=20)
    while True:
        try:
            with NFCReader(config.nfc_reader['input_device']) as card_reader:
                for uid_dec in card_reader.get_card_uid():
                    uid_endian = int(uid_dec)
                    uid_fixed = struct.unpack("<I", struct.pack(">I", uid_endian))[0]
                    uid = format(uid_fixed, "08x")
                    out.control_led(LEDs.RED_GREEN_BLINKING_ALTERNATELY)
                    auth_result = authenticate(uid)
                    if auth_result.isGranted:
                        if auth_result.type == AuthResult.TYPE_NORMAL:
                            log.info("Access granted by ERC: " + uid)
                            out.control_led(LEDs.GREEN_STATIC, duration=5)
                        elif auth_result.type == AuthResult.TYPE_HARDCODED:
                            log.info("Access granted by hardcoded IDs: " + uid)
                            out.control_led(LEDs.GREEN_BLINKING, frequency=0.3, number_of_blinks=17)
                        out.open_door()
                        sleep(1)
                    else:
                        if auth_result.type == AuthResult.TYPE_NORMAL:
                            log.info("Access denied by ERC: " + uid)
                            out.control_led(LEDs.RED_STATIC, duration=5)
                        elif auth_result.type == AuthResult.TYPE_HARDCODED:
                            log.info("Access denied by hardcoded IDs: " + uid)
                            out.control_led(LEDs.RED_BLINKING, frequency=0.3, number_of_blinks=17)
        except Exception as ex:
            log.error("MAIN LOOP EXCEPTION: " + str(ex))
            out.control_led(LEDs.RED_GREEN_BLINKING_TOGETHER, frequency=0.2, number_of_blinks=20)

        log.error("Restart main loop")


