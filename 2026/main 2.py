try:

    import cv2
    import go_to_ports
    import traceback
    from hard_control.abstractions import *
    from hard_control.hard_camera import *
    from hard_control.hard_motors import *
    import numpy as np
    import colors
    Yellow = colors.Yellow
    Green = colors.Green
    Red = colors.Red
    Orange = colors.Orange
    cam = HardCamera()
    motor_left = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
    motor_right = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
    time.sleep(3)


    queue = [Yellow, Green, Red]
    print()
    img = cam.get_frame()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)




    cntr = Point(img.shape[1::-1])/2
    PID_yaw = PID_regulator(-0.04, 0, 0, 0)
    PID_speed = PID_regulator(0.0004, 0, 0, 90000)

    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000),
                                       cv2.aruco.DetectorParameters())

    OUTPUT_FILE = "output.mp4"      # имя выходного файла
    FPS = 30*0.2                         # кадров в секунду
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # кодек для MP4
    out = cv2.VideoWriter(OUTPUT_FILE, fourcc, FPS, (cntr*2).to_int())


    def video_sleep(sleep_time, out, FPS, get_img):
        time_start = time.time()
        while time_start+sleep_time > time.time():
            # out.write(get_img())
            time.sleep(1/FPS)



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


    def getContoursColor(color):
        raw = cam.get_frame()
        hsv = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
        mask = inRangeF(hsv, color)
        # print(type(mask))
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        # print(type(contours))
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        # print(len(contours))
        return contours, raw


    def getCenter(contour):
        m = cv2.moments(contour)
        if m['m00'] > 0:
            color_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
            return color_cntr
        return None


    def rotateToColor(color, speed=30, reverse=False, duo=0):
        while True:
            contours, img = getContoursColor(color)
            out.write(cv2.drawContours(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), contours[:1 + duo], -1, (255, 0, 0), -1))
            if len(contours) >= 1 + duo and cv2.contourArea(contours[0 + duo]) > 500:
                motor_left.set_motor(0)
                motor_right.set_motor(0)
                break
            motor_left.set_motor(speed * ((2 * int(reverse)) - 1))
            motor_right.set_motor(speed * ((-2 * int(reverse)) + 1))


    def largest_contour(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return 0
        # Находим контур с максимальной площадью
        max_contour = max(contours, key=cv2.contourArea)
        return cv2.contourArea(max_contour)
    left_cntr = cntr-Point(200, 0)
    def go_to_gate_orange_and_rotate():
        rotateToColor(Orange, reverse=False, duo=1)
        while 1:
            c, raw = getContoursColor(Orange)
            masked = cv2.drawContours(cv2.cvtColor(raw, cv2.COLOR_BGR2RGB), c[:2], -1, (255, 0, 0), -1)
            print(len(c))
            if len(c) >= 2 and cv2.contourArea(c[1]) > 500:
                print(cv2.contourArea(c[1]))
                orange_cntr = getCenter(c[0])
                orange_cntr_2 = getCenter(c[1])
                cv2.circle(masked, orange_cntr.to_int(), 5, (0, 255, 0), 2)
                cv2.circle(masked, orange_cntr_2.to_int(), 5, (0, 0, 255), 2)
                cv2.circle(masked, ((orange_cntr + orange_cntr_2) / 2).to_int(), 5, (0, 255, 255), 2)
                out.write(masked)
                delta_x_yaw = (cntr - ((orange_cntr + orange_cntr_2) / 2)).x
                delta_x_speed = abs((orange_cntr - orange_cntr_2).x)
                u = PID_yaw(delta_x_yaw * 2)
                u_speed = PID_speed(delta_x_speed)
                print(u, u_speed)
                motor_left.set_motor(u_speed - u)
                motor_right.set_motor(u_speed + u)
            else:
                video_sleep(2, out, FPS, lambda: cam.get_frame())
                motor_left.set_motor(0)
                motor_right.set_motor(0)
                break


    # # Сортируем цвета по убыванию площади самого большого контура
    queue_sorted = sorted(queue, key=lambda x: largest_contour(inRangeF(hsv, x)), reverse=True)
    print(queue_sorted)






    # go_to_gate_orange_and_rotate()
    # out.release()
    # video_sleep(2, out, FPS, lambda: cam.get_frame())
    motor_left.set_motor(50)
    motor_right.set_motor(50)
    video_sleep(3, out, FPS, lambda: cam.get_frame())
    motor_left.set_motor(0)
    motor_right.set_motor(0)
    go_to_ports.run_go_to_ports(motor_left, motor_right, lambda: cam.get_frame(), out, FPS)

    # go_to_gate_orange_and_rotate()

    while 1:
        img = cam.get_frame()
        out.write(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if img is None:
            motor_left.set_motor(20)
            motor_right.set_motor(-20)
            continue

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        aruco = detector.detectMarkers(img)
        if aruco is None:
            motor_left.set_motor(20)
            motor_right.set_motor(-20)
            continue

        corners, ids, rejected = aruco  # распаковываем кортеж
        if ids is None or len(ids) == 0:
            motor_left.set_motor(20)
            motor_right.set_motor(-20)
            continue
        break
    while 1:
        img = cam.get_frame()
        if img is None:
            video_sleep(0.1, out, FPS, lambda: cam.get_frame())
            continue

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        aruco = detector.detectMarkers(img)
        if aruco is None:
            continue

        corners, ids, rejected = aruco  # распаковываем кортеж
        if ids is None or len(ids) == 0:
            video_sleep(0.1, out, FPS, lambda: cam.get_frame())
            continue
        out.write(cv2.aruco.drawDetectedMarkers(cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB), corners, ids))
        # Здесь ids – массив найденных id
        # Например, сортируем по убыванию id и берём первый маркер
        # Преобразуем ids в плоский список для удобства
        ids_flat = ids.flatten()
        # Индекс маркера с максимальным id
        best_idx = np.argmax(ids_flat)
        best_corner = corners[best_idx]

        # Вычисляем центр маркера (усреднение углов)
        corner_points = best_corner[0]  # массив 4x2
        center = Point(corner_points.mean(axis=0))

        # Здесь можно рисовать на img, если нужно
        # cv2.polylines(img, [corner_points.astype(int)], True, (0,255,0), 2)
        # cv2.circle(img, center.to_int(), 5, (0,0,255), -1)

        # Ваши расчёты
        c_area = abs(corner_points[1][0] - corner_points[0][0])
        if c_area > 130:
            video_sleep(3, out, FPS, lambda: cam.get_frame())
            motor_left.set_motor(0)
            motor_right.set_motor(0)
            break
        u = PID_yaw((left_cntr - center).x*1.5)
        u_speed = PID_speed(c_area*1.5)
        # print(u, u_speed)
        print(c_area)
        motor_left.set_motor(u_speed - u)
        motor_right.set_motor(u_speed + u)

        # Если нужно записывать видео с отрисованными маркерами:
        # out.write(img)



    input('end?')
except:
    try:
        motor_left.set_motor(0)
        motor_right.set_motor(0)
        motor_left.stop()
        motor_right.stop()
        out.release()
        print("Произошла ошибка:")
        traceback.print_exc()
    except BaseException as e:
        print(type(e).__name__, e)
motor_left.set_motor(0)
motor_right.set_motor(0)
motor_left.stop()
motor_right.stop()
out.release()

