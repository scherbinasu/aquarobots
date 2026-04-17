import cv2
import time
from hard_control.abstractions import *
# from hard_control.hard_camera import *
import app
from hard_control.hard_motors import *
import numpy as np
# cam = HardCamera()
motor_left = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
motor_right = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
time.sleep(3)
Yellow = {"obrez":"80","h_min":"66","s_min":"60","s_max":"171","v_min":"179","v_max":"255","h_max":"98", 'stop_area': 90000}
Green = {"obrez":"80","h_min":"46","s_min":"114","s_max":"240","v_min":"102","v_max":"249","h_max":"76", 'stop_area': 22500}
Red = {"obrez": "80", "h_min": "103", "s_min": "84", "s_max": "255", "v_min": "73", "v_max": "255", "h_max": "179", 'stop_area': 100000}
Orange = {"obrez":"80","h_min":"101","s_min":"197","s_max":"255","v_min":"174","v_max":"255","h_max":"116"}


queue = [Yellow, Green, Red]
while app.raw is None:
    time.sleep(0.1)
    print('.', end='')
print()
img = app.cap.get_frame()
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
cntr = Point(img.shape[1::-1])/2
PID_yaw = PID_regulator(-0.04, 0, 0, 0)
PID_speed = PID_regulator(0.00048, 0, 0, 90000)

def inRangeF(img, color):
    """Возвращает бинарную маску для заданного цвета."""
    lower = (int(color['h_min']), int(color['s_min']), int(color['v_min']))
    upper = (int(color['h_max']), int(color['s_max']), int(color['v_max']))
    app.masked = cv2.inRange(img, lower, upper)
    # Обрезка верхней части
    obrez = int(color['obrez'])
    if obrez > 0:
        app.masked[:obrez, :] = 0

    # print(cv2.countNonZero(mask))
    # cv2.imwrite(color['h_min'] + '.jpg', mask)
    return app.masked


def getContoursColor(color):
    app.raw = app.cap.get_frame()
    hsv = cv2.cvtColor(app.raw, cv2.COLOR_BGR2HSV)
    mask = inRangeF(hsv, color)
    # print(type(mask))
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    # print(type(contours))
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    # print(len(contours))
    return contours


def getCenter(contour):
    m = cv2.moments(contour)
    if m['m00'] > 0:
        color_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
        return color_cntr
    return None

def rotateToColor(color, speed=20, reverse=False, duo=False):
    while True:
        contours = getContoursColor(color)
        if len(contours) >= 1+duo and cv2.contourArea(contours[0+duo]) > 1500:break
        motor_left.set_motor(speed*((2*int(reverse))-1))
        motor_right.set_motor(speed*((-2*int(reverse))+1))

rotateToColor(Orange, duo=True)
while 1:
    c = getContoursColor(Orange)
    app.masked = cv2.drawContours(np.zeros(app.raw.shape), c[:2], -1, (255, 0, 0), -1)
    print(len(c))
    if len(c) >= 2 and cv2.contourArea(c[1]) > 1500:
        print(cv2.contourArea(c[1]))
        orange_cntr = getCenter(c[0])
        orange_cntr_2 = getCenter(c[1])
        cv2.circle(app.masked, orange_cntr.to_int(), 5, (0, 255, 0), 2)
        cv2.circle(app.masked, orange_cntr_2.to_int(), 5, (0, 0, 255), 2)
        cv2.circle(app.masked, ((orange_cntr+orange_cntr_2)/2).to_int(), 5, (0, 255, 255), 2)
        delta_x_yaw = (cntr - ((orange_cntr+orange_cntr_2)/2)).x
        delta_x_speed = abs((orange_cntr - orange_cntr_2).x)
        u = PID_yaw(delta_x_yaw*1.5)
        u_speed = PID_speed(delta_x_speed)
        print(u, u_speed)
        motor_left.set_motor(u_speed - u)
        motor_right.set_motor(u_speed + u)
    else:
        motor_left.set_motor(0)
        motor_right.set_motor(0)
        break
input('end?')


