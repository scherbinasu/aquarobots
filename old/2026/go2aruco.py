from hard_control.hard_motors import *
import traceback
from hard_control.hard_camera import *
from hard_control.abstractions import *
motor_left = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
motor_right = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
cam = HardCamera()
time.sleep(3)
def mv(speed_left, speed_right, delay):
    print("Motor started", speed_left, speed_right, delay)
    motor_left.set_motor(speed_left)
    motor_right.set_motor(speed_right)
    time.sleep(delay)
def stop():
    motor_left.stop()
    motor_right.stop()
try:
    PID_yaw = PID_regulator(-0.04, 0, 0, 0)
    PID_speed = PID_regulator(0.0004, 0, 0, 90000)
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000),
                                       cv2.aruco.DetectorParameters())
    img = cam.get_frame()
    cntr = Point(img.shape[1::-1])/2

    while True:
        flag = True
        img = cam.get_frame()
        if not img is None:

            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            aruco = detector.detectMarkers(img)
            if not aruco is None:

                corners, ids, rejected = aruco  # распаковываем кортеж
                if not ids is None and len(ids) != 0:
                    for id_i in range(len(ids)):
                        if ids[id_i][0] == 239:
                            best_corner = corners[id_i]

                            # Вычисляем центр маркера (усреднение углов)
                            corner_points = best_corner[0]  # массив 4x2
                            center = Point(corner_points.mean(axis=0))

                            # Здесь можно рисовать на img, если нужно
                            # cv2.polylines(img, [corner_points.astype(int)], True, (0,255,0), 2)
                            # cv2.circle(img, center.to_int(), 5, (0,0,255), -1)

                            # Ваши расчёты
                            c_area = abs(corner_points[1][0] - corner_points[0][0])
                            u = PID_yaw((cntr - center).x * 1.5)
                            u_speed = PID_speed(c_area * 1.5)
                            # print(u, u_speed)
                            print(c_area, u_speed, u)
                            motor_left.set_motor(-u_speed - u)
                            motor_right.set_motor(-u_speed + u)
                            flag=False
        if flag:
            print('nazad')
            motor_left.set_motor( 35)
            motor_right.set_motor(35)


except:
    traceback.print_exc()
stop()