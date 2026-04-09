from hard_control.hard_motors import *
import traceback, random
motor_left = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
motor_right = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
time.sleep(3)
def mv(speed_left, speed_right, delay):
    print("Motor started", speed_left, speed_right, delay)
    motor_left.set_motor(-speed_left*1.25)
    motor_right.set_motor(-speed_right)
    time.sleep(delay)
def stop():
    motor_left.stop()
    motor_right.stop()
try:
    mv(50, 50, 5)
    # input("Press Enter to continue...")
    mv(50, 50, 5)
    if 0:
        mv(-30, -30, 2)
        mv(30, -30, 2)
        mv(30, 30, 3)
        mv(-30, -30, 5)
        mv(30, 30, 3)
        mv(30, -30, 2.5)
        mv(100, 100, 10)
    else:
        time_start = time.time()
        while time_start+300 > time.time():
            mv(random.randint(-10, 10)*10, random.randint(-10, 10)*10, random.randint(10, 50)/10)




except:
    traceback.print_exc()
stop()