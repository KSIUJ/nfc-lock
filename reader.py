import subprocess
import signal
import evdev


class NFCReader:
    singleton = None

    def __init__(self, devPath):
        self.devPath = devPath

    class _NFCReader:
        def __init__(self, devPath):
            self.dev = evdev.InputDevice(devPath)

        def get_card_uid(self):
            buf = ''
            for event in self.dev.read_loop():
                if event.type == evdev.ecodes.EV_KEY:
                    k = evdev.events.KeyEvent(event)
                    if k.keystate == evdev.events.KeyEvent.key_down:
                        key = self.process_key(k.keycode)
                        if key == 'E':
                            yield buf
                            buf = ''
                        else:
                            buf += key

        def process_key(self, keycode):
            if keycode[:4] == 'KEY_':
                if keycode[4:] == 'ENTER':
                    return 'E'

                try:
                    int(keycode[4:])
                except ValueError:
                    return '';

                return keycode[4:]

    def __enter__(self):
        if NFCReader.singleton is not None:
            raise Exception("Only one NFCReader instance allowed")

        NFCReader.singleton = self._NFCReader(self.devPath)
        return NFCReader.singleton

    def __exit__(self, exc_type, exc_val, exc_tb):
        NFCReader.singleton = None
