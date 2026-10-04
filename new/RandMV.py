from robot.control.motor.motors import *
import traceback, random, time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN)
motor_left = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
motor_right = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
motor_left.start()
motor_right.start()
time.sleep(3)
while True:
    if not GPIO.input(4):
        print("ОооооООо, ДААааАааАА\n"*10)
        break
    else:
        print("Нажми меня ***")
        time.sleep(0.01)
def mv(speed_left, speed_right, delay):
    print("Motor started", speed_left, speed_right, delay)
    motor_left.set_motor(speed_left*1.25)
    motor_right.set_motor(speed_right)
    time.sleep(delay)
def stop():
    motor_left.stop()
    motor_right.stop()
try:
    mv(50, 50, 10)
    time_start = time.time()
    while time_start+250 > time.time():
        mv(random.randint(-10, 10)*10, random.randint(-10, 10)*10, random.randint(10, 30)/10)
    mv(100, 100, 600)
except:
    traceback.print_exc()
stop()
