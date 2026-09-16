import auth
from auth import authenticate, AuthResult
from reader import NFCReader
from gpio import Outputs, LEDs
from time import sleep
from threading import Thread
from logger import Logger

import config.main as config

import struct

log = Logger().getLog()

# How often the app re-pulls the UID/card lists from ERC and flushes any
# queued events. Owned here (rather than inside auth.py) since it's an
# application-level scheduling concern.
REFRESH_INTERVAL_SECONDS = 60 * 60

# How often the app retries events that couldn't be sent to ERC directly
# (see auth.queue_event) and are sitting in the on-disk queue.
EVENT_RETRY_INTERVAL_SECONDS = 10


def _periodic_sync():
    while True:
        sleep(REFRESH_INTERVAL_SECONDS)
        log.info('Periodic ERC sync')
        auth.sync()


def _periodic_event_flush():
    while True:
        sleep(EVENT_RETRY_INTERVAL_SECONDS)
        auth.flush_queue()


with Outputs() as out:
    log.info('Loading card cache and syncing with ERC')
    auth.load()
    auth.sync()
    Thread(target=_periodic_sync, daemon=True).start()
    Thread(target=_periodic_event_flush, daemon=True).start()
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
                            log.info(f"Access granted by ERC: {uid} ({auth_result.reason})")
                            out.control_led(LEDs.GREEN_STATIC, duration=5)
                        elif auth_result.type == AuthResult.TYPE_OFFLINE:
                            log.info(f"Access granted offline (ERC unreachable): {uid} ({auth_result.reason})")
                            out.control_led(LEDs.GREEN_BLINKING, frequency=0.3, number_of_blinks=17)
                        out.open_door()
                        sleep(1)
                    else:
                        if auth_result.type == AuthResult.TYPE_NORMAL:
                            log.info(f"Access denied by ERC: {uid} ({auth_result.reason})")
                            out.control_led(LEDs.RED_STATIC, duration=5)
                        elif auth_result.type == AuthResult.TYPE_OFFLINE:
                            log.info(f"Access denied offline (ERC unreachable): {uid} ({auth_result.reason})")
                            out.control_led(LEDs.RED_BLINKING, frequency=0.3, number_of_blinks=17)
        except Exception as ex:
            log.error("MAIN LOOP EXCEPTION: " + str(ex))
            out.control_led(LEDs.RED_GREEN_BLINKING_TOGETHER, frequency=0.2, number_of_blinks=20)

        log.error("Restart main loop")


