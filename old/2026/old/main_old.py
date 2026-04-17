import cv2
import time
from hard_control.abstractions import *
# from hard_control.hard_camera import *
if __name__ == '__main__':
    import app_old as app
    from hard_control.hard_motors import *
import numpy as np
# cam = HardCamera()
if __name__ == '__main__':
    motor_left = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
    motor_right = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
    time.sleep(3)
    Yellow = {"obrez":"80","h_min":"66","s_min":"60","s_max":"171","v_min":"179","v_max":"255","h_max":"98", 'stop_area': 90000}
    Green = {"obrez":"80","h_min":"46","s_min":"114","s_max":"240","v_min":"102","v_max":"249","h_max":"76", 'stop_area': 22500}
    Red = {"obrez": "80", "h_min": "103", "s_min": "84", "s_max": "255", "v_min": "73", "v_max": "255", "h_max": "179", 'stop_area': 90000}
    Orange = {"obrez": "80", "h_min": "94", "s_min": "174", "s_max": "255", "v_min": "195", "v_max": "255", "h_max": "105"}

    queue = [Yellow, Green, Red]
    while app.raw is None:
        time.sleep(0.1)
        print('.', end='')
    print()
    img = app.raw
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


    def inRangeF(img, color):
        """Возвращает бинарную маску для заданного цвета."""
        lower = (int(color['h_min']), int(color['s_min']), int(color['v_min']))
        upper = (int(color['h_max']), int(color['s_max']), int(color['v_max']))
        mask = cv2.inRange(img, lower, upper)
        # Обрезка верхней части
        obrez = int(color['obrez'])
        if obrez > 0:
            mask[:obrez, :] = 0
        # print(cv2.countNonZero(mask))
        # cv2.imwrite(color['h_min'] + '.jpg', mask)
        return mask


    def largest_contour(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return 0
        # Находим контур с максимальной площадью
        max_contour = max(contours, key=cv2.contourArea)
        return cv2.contourArea(max_contour)


    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100),
                                       cv2.aruco.DetectorParameters())
    # # Сортируем цвета по убыванию площади самого большого контура
    queue_sorted = sorted(queue, key=lambda x: largest_contour(inRangeF(hsv, x)), reverse=True)
    print(queue_sorted)
    # queue_sorted = [Red, Yellow, Green]

    cntr = Point(img.shape[1::-1])/2
    contours = [0, 0]
    PID_yaw = PID_regulator(-0.04, 0, 0, 0)
    PID_speed = PID_regulator(0.00048, 0, 0, 90000)
    # while len(contours) >= 2:
    #     img = frame_raw
    #     hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    #     mask = inRangeF(hsv, Orange)
    #     contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    #     contours = sorted(contours, key=cv2.contourArea, reverse=True)
    #     if len(contours) >= 2:
    #         br = np.zeros(mask.shape)
    #         br = cv2.drawContours(br, contours[:2], -1, 255, cv2.FILLED)
    #         m = cv2.moments(br)
    #         print('000', m['m00'])
    #         if m['m00'] > 100:
    #             orange_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
    #             u = PID_yaw((cntr - orange_cntr).x)
    #             motor_left.set_motor(30 - u)
    #             motor_right.set_motor(30 + u)
    #             print('111', u)
    #         else:
    #             break
    # input(322)
else:
    def inRangeF(img, color):
        """Возвращает бинарную маску для заданного цвета."""
        lower = (int(color['h_min']), int(color['s_min']), int(color['v_min']))
        upper = (int(color['h_max']), int(color['s_max']), int(color['v_max']))
        masked = cv2.inRange(img, lower, upper)
        # Обрезка верхней части
        obrez = int(color['obrez'])
        if obrez > 0:
            masked[:obrez, :] = 0

        # print(cv2.countNonZero(mask))
        # cv2.imwrite(color['h_min'] + '.jpg', mask)
        return masked


    def getCenter(contour):
        m = cv2.moments(contour)
        if m['m00'] > 0:
            color_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
            return color_cntr
        return None


    def largest_contour(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return 0
        # Находим контур с максимальной площадью
        max_contour = max(contours, key=cv2.contourArea)
        return cv2.contourArea(max_contour)

def run_port(func_cam, motor_left, motor_right, queue_sorted, PID_yaw, PID_speed):

    for i in range(len(queue_sorted)):
        color = queue_sorted[i]
        c_area = 0
        motor_left.set_motor(0)
        motor_right.set_motor(0)
        while True:
            img = func_cam()
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = inRangeF(hsv, color)
            contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            if len(contours) >= 1 and cv2.contourArea(contours[0]) > 6000:break
            motor_left.set_motor(-20)
            motor_right.set_motor(20)
        while c_area <= color['stop_area']:
            img = func_cam()
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = inRangeF(hsv, color)
            contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            print('contours', len(contours))
            if len(contours) >= 1:
                c_area = cv2.contourArea(contours[0])
                print('c area', c_area)
                if c_area > 1000:
                    # br = np.zeros(mask.shape)
                    # br = cv2.drawContours(br, contours[0], -1, 255, cv2.FILLED)
                    m = cv2.moments(contours[0])
                    if m['m00'] > 0:
                        masked = img
                        color_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
                        cv2.circle(masked, color_cntr.to_int(), 5, (0, 0, 255), cv2.FILLED)
                        cv2.circle(masked, cntr.to_int(), 10, (255, 0, 0), cv2.FILLED)
                        delta_x = (cntr - color_cntr).x
                        u = PID_yaw(delta_x)
                        u_speed = PID_speed(c_area)
                        motor_left.set_motor(u_speed - u)
                        motor_right.set_motor(u_speed + u)
                        print('speed, yaw, delta', u_speed, u, delta_x)
                else:
                    break
        time.sleep(2)
        motor_left.set_motor(-35)
        motor_right.set_motor(-35)
        time.sleep(1)
        motor_left.set_motor(0)
        motor_right.set_motor(0)
        time.sleep(1)
if __name__ == '__main__':
    run_port(lambda: app.raw, motor_left, motor_right, queue_sorted, PID_yaw, PID_speed)
    cv2.imwrite('1.jpg', img)
    motor_left.set_motor(0)
    motor_right.set_motor(0)
    motor_left.stop()
    motor_right.stop()
    print('stopped')
    while 1:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    app.cap.release()
    exit()

    # почти проплыли ворота
        # ==================================#
        # ЧТО-ТО ДЛЯ ЗАВЕРШЕНИЯ ПОРТОВКЕ#
        # ==================================#
    while 1:
        img = cam.get_frame()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = inRangeF(hsv, Orange)
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        motor_left.set_motor(20)
        motor_right.set_motor(-20)
        if len(contours) > 1:
            if cv2.contourArea(contours[0])+cv2.contourArea(contours[1]) > 200:
                break
    while len(contours) >= 2:
        img = cam.get_frame()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = inRangeF(hsv, Orange)
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        if len(contours) >= 2:
            br = np.zeros(mask.shape)
            br = cv2.drawContours(br, contours[:2], -1, 255, cv2.FILLED)
            m = cv2.moments(br)
            if m['m00'] > 100:
                orange_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
                u = PID_yaw((cntr - orange_cntr).x)
                motor_left.set_motor(30 - u)
                motor_right.set_motor(30 + u)
            else:
                break

    while c_area <= 100:
        img = cam.get_frame()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        data_map_aruco = detector.detectMarkers(img)  # corners, ids, rejected
        data_map_aruco = sorted(data_map_aruco, key=lambda x: x[1], reverse=True)
        if len(data_map_aruco) >= 1:
            marker_corners = data_map_aruco[0][0]
            c_area = (Point(marker_corners[1]) + Point(marker_corners[0])) / 2
            color_cntr = Point(marker_corners.mean(axis=0))
            u = PID_yaw((cntr - color_cntr).x)
            u_speed = PID_speed(c_area)
            motor_left.set_motor(u_speed - u)
            motor_right.set_motor(u_speed + u)
    motor_left.set_motor(0)
    motor_right.set_motor(0)
    motor_left.stop()
    motor_right.stop()
    cam.release()
