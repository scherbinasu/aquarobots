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
Orange = {"obrez": "80", "h_min": "94", "s_min": "174", "s_max": "255", "v_min": "195", "v_max": "255", "h_max": "105"}

queue = [Yellow, Green, Red]
while app.raw is None:
    time.sleep(0.1)
    print('.', end='')
print()
img = app.cap.get_frame()
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


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

def rotateToColor(color, speed=20, reverse=False):
    while True:
        contours = getContoursColor(color)
        if len(contours) >= 1 and cv2.contourArea(contours[0]) > 8000:break
        motor_left.set_motor(speed*((2*int(reverse))-1))
        motor_right.set_motor(speed*((-2*int(reverse))+1))



cntr = Point(img.shape[1::-1])/2
PID_yaw = PID_regulator(-0.04, 0, 0, 0)
PID_speed = PID_regulator(0.00048, 0, 0, 90000)
detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100),
                                   cv2.aruco.DetectorParameters())




queue_sorted = sorted(queue, key=lambda x: (getCenter(getContoursColor(x)[0])-cntr).x, reverse=True)
print(queue_sorted)
for color in queue_sorted:
    rotateToColor(color)
    while 1:
        contours = getContoursColor(color)
        c_area = cv2.contourArea(contours[0])
        if color['stop_area'] < c_area or c_area < 500: break
        print('c_area', c_area, color['stop_area'])
        color_cntr = getCenter(contours[0])
        if color_cntr is not None:
            cv2.circle(app.masked, color_cntr.to_int(), 5, (0, 0, 255), cv2.FILLED)
            cv2.circle(app.masked, cntr.to_int(), 10, (255, 0, 0), cv2.FILLED)
            delta_x = (cntr - color_cntr).x
            u = PID_yaw(delta_x)
            u_speed = PID_speed(c_area, setpoint=color['stop_area'])
            motor_left.set_motor(u_speed - u)
            motor_right.set_motor(u_speed + u)
            print('speed, yaw, delta', u_speed, u, delta_x)
        # if color['stop_area'] < c_area < 500: break
    time.sleep(2)
    motor_left.set_motor(-30)
    motor_right.set_motor(-30)
    time.sleep(2)
    motor_left.set_motor(0)
    motor_right.set_motor(0)
    time.sleep(1)


