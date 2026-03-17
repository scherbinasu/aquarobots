from hard_control.hard_motors import *
import time
try:
    motor_left = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
    motor_right = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
    time.sleep(2)
    motor_left.set_motor(-90)
    motor_right.set_motor(90)
    time.sleep(100000)
except KeyboardInterrupt:pass
motor_left.set_motor(0)
motor_right.set_motor(0)
motor_left.stop()
motor_right.stop()