from hard_control.hard_motors import *
import traceback
motor_left = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
motor_right = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
def motor(speed_left, speed_right, delay):
    motor_left.set_motor(speed_left)
    motor_right.set_motor(speed_right)
    time.sleep(delay)
def stop():
    motor_left.stop()
    motor_right.stop()
try:pass

except:
    traceback.print_exc()
stop()