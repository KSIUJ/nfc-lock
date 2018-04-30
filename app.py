from auth import authenticate
from reader import NFCReader
from lock import DoorLock
from display import lcd
from time import sleep

screen = lcd()
error_count = 0

with DoorLock() as lock, NFCReader() as reader:
    while True:
        try:
            screen.lcd_clear()
            screen.lcd_display_string(" Kolo Studentow", 1)
            screen.lcd_display_string("  Informatyki", 2)

            uid = reader.get_card_uid()
            if authenticate(uid):
                print("Access granted: " + uid)
                lock.open_door()
                screen.lcd_clear()
                screen.lcd_display_string("   Door open", 1)
                screen.lcd_display_string("Welcome to KSI!", 2)
            else:
                print("Access denied: " + uid)
                screen.lcd_clear()
                screen.lcd_display_string("  Unauthorized ", 1)
                screen.lcd_display_string(" Access denied!", 2)
            sleep(5)
            error_count = 0
        except Exception as ex:
            if error_count < 10:
                backoff = 2 ** error_count
                print(ex)
                print("Error, restarting in " + str(backoff))
                screen.lcd_clear()
                screen.lcd_display_string("     ERROR", 1)
                screen.lcd_display_string("Reset in " + str(backoff) + "s", 2)
                sleep(backoff)
                error_count += 1
            else:
                screen.lcd_clear()
                screen.lcd_display_string("  System error", 1)
                raise
