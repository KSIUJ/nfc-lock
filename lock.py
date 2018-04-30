import RPi.GPIO as GPIO
import time


class DoorLock:
    CHANNEL = 40
    singleton = None

    class _DoorLock:
        def open_door(self):
            GPIO.output(DoorLock.CHANNEL, 1)
            time.sleep(0.1)
            GPIO.output(DoorLock.CHANNEL, 0)

    def __enter__(self):
        if DoorLock.singleton is not None:
            raise Exception("Only one DoorLock instance allowed")
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(DoorLock.CHANNEL, GPIO.OUT)
        DoorLock.singleton = DoorLock._DoorLock()
        return DoorLock.singleton

    def __exit__(self, exc_type, exc_val, exc_tb):
        GPIO.cleanup()
        DoorLock.singleton = None
