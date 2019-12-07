import RPi.GPIO as GPIO
import time
from threading import Thread

import config.main as config


class Outputs:
    LOCK_CHANNEL = config.lock['lock_gpio']
    LOCK_OPEN_STATE = GPIO.HIGH if config.lock['lock_reversed'] else GPIO.LOW
    LOCK_CLOSE_STATE = GPIO.LOW if config.lock['lock_reversed'] else GPIO.HIGH

    GREEN_LED_CHANNEL = config.led['green_gpio']
    GREEN_LED_ON_STATE = GPIO.LOW if config.led['green_reversed'] else GPIO.HIGH
    GREEN_LED_OFF_STATE = GPIO.HIGH if config.led['green_reversed'] else GPIO.LOW

    RED_LED_CHANNEL = config.led['red_gpio']
    RED_LED_ON_STATE = GPIO.LOW if config.led['red_reversed'] else GPIO.HIGH
    RED_LED_OFF_STATE = GPIO.HIGH if config.led['red_reversed'] else GPIO.LOW

    singleton = None
    leds_thread = None

    class _Outputs:
        def open_door(self):
            GPIO.output(Outputs.LOCK_CHANNEL, Outputs.LOCK_OPEN_STATE)
            time.sleep(config.lock['opening_time'])
            GPIO.output(Outputs.LOCK_CHANNEL, Outputs.LOCK_CLOSE_STATE)

        def control_led(self, type, frequency=0.1, number_of_blinks=-1, duration=-1):
            if Outputs.leds_thread is not None:
                Outputs.leds_thread.stop()
                Outputs.leds_thread.join()
            Outputs.leds_thread = LEDs()
            Outputs.leds_thread.set_params(type, frequency, number_of_blinks, duration)
            Outputs.leds_thread.start()

    def __enter__(self):
        if Outputs.singleton is None:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(Outputs.LOCK_CHANNEL, GPIO.OUT)
            GPIO.output(Outputs.LOCK_CHANNEL, Outputs.LOCK_CLOSE_STATE)
            GPIO.setup(Outputs.GREEN_LED_CHANNEL, GPIO.OUT)
            GPIO.output(Outputs.GREEN_LED_CHANNEL, GPIO.LOW)
            GPIO.setup(Outputs.RED_LED_CHANNEL, GPIO.OUT)
            GPIO.output(Outputs.RED_LED_CHANNEL, GPIO.LOW)
            Outputs.singleton = Outputs._Outputs()
        return Outputs.singleton

    def __exit__(self, exc_type, exc_val, exc_tb):
        GPIO.cleanup()
        Outputs.singleton = None


class LEDs(Thread):
    TURN_OFF = 0
    RED_GREEN_STATIC = 1
    RED_GREEN_BLINKING_ALTERNATELY = 2
    RED_GREEN_BLINKING_TOGETHER = 3
    RED_STATIC = 4
    GREEN_STATIC = 5
    RED_BLINKING = 6
    GREEN_BLINKING = 7
    RED_SOFT_DIMM_IN_OUT = 8
    GREEN_SOFT_DIMM_IN_OUT = 9
    RED_GREEN_DIMM_IN_OUT_ALTERNATELY = 10
    RED_GREEN_DIMM_IN_OUT_TOGETHER = 11

    RED_PWM_FREQUENCY = 50
    RED_PWM_STEP = 10
    GREEN_PWM_FREQUENCY = 50
    GREEN_PWM_STEP = 10

    def set_params(self, type, frequency=0.1, number_of_blinks=-1, duration=-1):
        self.type = type
        self.frequency = frequency
        self.number_of_blinks = number_of_blinks
        self.duration = duration
        self.stopThread = False
        self.red_pwm = None
        self.green_pwm = None

    def stop(self):
        self.stopThread = True

    def easing_function(self, x):
        return x*x*0.01

    def start_pwm_red(self):
        self.red_pwm = GPIO.PWM(Outputs.RED_LED_CHANNEL, LEDs.RED_PWM_FREQUENCY)
        self.red_pwm.start(0)

    def stop_pwm_red(self):
        self.red_pwm.stop()
        self.red_pwm = None

    def start_pwm_green(self):
        self.green_pwm = GPIO.PWM(Outputs.GREEN_LED_CHANNEL, LEDs.GREEN_PWM_FREQUENCY)
        self.green_pwm.start(0)

    def stop_pwm_green(self):
        self.green_pwm.stop()
        self.green_pwm = None

    def run(self):
        if self.type == LEDs.TURN_OFF:
            GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
            GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
            return

        if self.type == LEDs.RED_GREEN_STATIC:
            GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_ON_STATE)
            GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_ON_STATE)
            if self.duration > -1:
                n = round(float(self.duration) / 0.1)
                while n > 0:
                    if self.stopThread:
                        return
                    time.sleep(0.1)
                    n -= 1
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
            return

        if self.type == LEDs.RED_GREEN_BLINKING_ALTERNATELY:
            GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                if self.stopThread:
                    return
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_ON_STATE)
                time.sleep(self.frequency)
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
                if self.stopThread:
                    return
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_ON_STATE)
                time.sleep(self.frequency)
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
                if self.stopThread:
                    return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1

        if self.type == LEDs.RED_GREEN_BLINKING_TOGETHER:
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                if self.stopThread:
                    return
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_ON_STATE)
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_ON_STATE)
                time.sleep(self.frequency)
                if self.stopThread:
                    return
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
                time.sleep(self.frequency)
                if self.stopThread:
                    return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1

        if self.type == LEDs.RED_STATIC:
            GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_ON_STATE)
            GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
            if self.duration > -1:
                n = round(float(self.duration) / 0.1)
                while n > 0:
                    if self.stopThread:
                        return
                    time.sleep(0.1)
                    n -= 1
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
            return

        if self.type == LEDs.GREEN_STATIC:
            GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
            GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_ON_STATE)
            if self.duration > -1:
                n = round(float(self.duration) / 0.1)
                while n > 0:
                    if self.stopThread:
                        return
                    time.sleep(0.1)
                    n -= 1
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
            return

        if self.type == LEDs.RED_BLINKING:
            GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_ON_STATE)
                time.sleep(self.frequency)
                if self.stopThread:
                    return
                GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
                time.sleep(self.frequency)
                if self.stopThread:
                    return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1

        if self.type == LEDs.GREEN_BLINKING:
            GPIO.output(Outputs.RED_LED_CHANNEL, Outputs.RED_LED_OFF_STATE)
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_ON_STATE)
                time.sleep(self.frequency)
                if self.stopThread:
                    return
                GPIO.output(Outputs.GREEN_LED_CHANNEL, Outputs.GREEN_LED_OFF_STATE)
                time.sleep(self.frequency)
                if self.stopThread:
                    return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1

        if self.type == LEDs.RED_SOFT_DIMM_IN_OUT:
            self.start_pwm_red()
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                for d in range(0, 101, LEDs.RED_PWM_STEP):
                    self.red_pwm.ChangeDutyCycle(self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.RED_PWM_STEP)))
                    if self.stopThread:
                        self.stop_pwm_red()
                        return
                for d in range(100, -1, -LEDs.RED_PWM_STEP):
                    self.red_pwm.ChangeDutyCycle(self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.RED_PWM_STEP)))
                    if self.stopThread:
                        self.stop_pwm_red()
                        return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1
            self.stop_pwm_red()

        if self.type == LEDs.GREEN_SOFT_DIMM_IN_OUT:
            self.start_pwm_green()
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                for d in range(0, 101, LEDs.GREEN_PWM_STEP):
                    self.green_pwm.ChangeDutyCycle(self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.GREEN_PWM_STEP)))
                    if self.stopThread:
                        self.stop_pwm_green()
                        return
                for d in range(100, -1, -LEDs.GREEN_PWM_STEP):
                    self.green_pwm.ChangeDutyCycle(self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.GREEN_PWM_STEP)))
                    if self.stopThread:
                        self.stop_pwm_green()
                        return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1
            self.stop_pwm_green()

        if self.type == LEDs.RED_GREEN_DIMM_IN_OUT_ALTERNATELY:
            self.green_pwm = GPIO.PWM(Outputs.GREEN_LED_CHANNEL, LEDs.GREEN_PWM_FREQUENCY)
            self.green_pwm.start(0)
            self.red_pwm = GPIO.PWM(Outputs.RED_LED_CHANNEL, LEDs.RED_PWM_FREQUENCY)
            self.red_pwm.start(0)
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                for d in range(0, 101, LEDs.RED_PWM_STEP):
                    self.red_pwm.ChangeDutyCycle(self.easing_function(d))
                    self.green_pwm.ChangeDutyCycle(100.0 - self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.RED_PWM_STEP)))
                    if self.stopThread:
                        self.red_pwm.stop()
                        self.red_pwm = None
                        self.green_pwm.stop()
                        self.green_pwm = None
                        return
                for d in range(100, -1, -LEDs.GREEN_PWM_STEP):
                    self.red_pwm.ChangeDutyCycle(self.easing_function(d))
                    self.green_pwm.ChangeDutyCycle(100.0 - self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.GREEN_PWM_STEP)))
                    if self.stopThread:
                        self.red_pwm.stop()
                        self.red_pwm = None
                        self.green_pwm.stop()
                        self.green_pwm = None
                        return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1
            self.red_pwm.stop()
            self.red_pwm = None
            self.green_pwm.stop()
            self.green_pwm = None

        if self.type == LEDs.RED_GREEN_DIMM_IN_OUT_TOGETHER:
            self.green_pwm = GPIO.PWM(Outputs.GREEN_LED_CHANNEL, LEDs.GREEN_PWM_FREQUENCY)
            self.green_pwm.start(0)
            self.red_pwm = GPIO.PWM(Outputs.RED_LED_CHANNEL, LEDs.RED_PWM_FREQUENCY)
            self.red_pwm.start(0)
            while self.number_of_blinks == -1 or self.number_of_blinks > 0:
                for d in range(0, 101, LEDs.RED_PWM_STEP):
                    self.red_pwm.ChangeDutyCycle(self.easing_function(d))
                    self.green_pwm.ChangeDutyCycle(self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.RED_PWM_STEP)))
                    if self.stopThread:
                        self.red_pwm.stop()
                        self.red_pwm = None
                        self.green_pwm.stop()
                        self.green_pwm = None
                        return
                for d in range(100, -1, -LEDs.GREEN_PWM_STEP):
                    self.red_pwm.ChangeDutyCycle(self.easing_function(d))
                    self.green_pwm.ChangeDutyCycle(self.easing_function(d))
                    time.sleep(self.frequency/(100.0/float(LEDs.GREEN_PWM_STEP)))
                    if self.stopThread:
                        self.red_pwm.stop()
                        self.red_pwm = None
                        self.green_pwm.stop()
                        self.green_pwm = None
                        return
                if self.number_of_blinks != -1:
                    self.number_of_blinks -= 1
            self.red_pwm.stop()
            self.red_pwm = None
            self.green_pwm.stop()
            self.green_pwm = None