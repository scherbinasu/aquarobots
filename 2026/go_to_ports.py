import cv2
import traceback
from hard_control.abstractions import *
from hard_control.hard_camera import *
from hard_control.hard_motors import *
import numpy as np

cam = HardCamera()
motor_left = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
motor_right = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
time.sleep(3)
Yellow = {"obrez": "170", "h_min": "87", "s_min": "92", "s_max": "255", "v_min": "179", "v_max": "255", "h_max": "99",
          'stop_area': 90000}
Green = {"obrez":"170","h_min":"60","s_min":"127","s_max":"255","v_min":"102","v_max":"255","h_max":"84",
         'stop_area': 92000}
Red = {"obrez": "170", "h_min": "103", "s_min": "84", "s_max": "255", "v_min": "73", "v_max": "255", "h_max": "179",
       'stop_area': 100000}
Orange = {"obrez": "170", "h_min": "101", "s_min": "197", "s_max": "255", "v_min": "174", "v_max": "255",
          "h_max": "116"}

queue = [Yellow, Green, Red]
queue_name = ['Yellow', 'Green', 'Red']
print()
img = cam.get_frame()
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

cntr = Point(img.shape[1::-1]) / 2
PID_yaw = PID_regulator(-0.04, 0, 0, 0)
PID_speed = PID_regulator(0.0005, 0, 0, 90000)

detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100),
                                   cv2.aruco.DetectorParameters())

OUTPUT_FILE = "output.mp4"  # имя выходного файла
FPS = 30  # кадров в секунду
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # кодек для MP4
out = cv2.VideoWriter(OUTPUT_FILE, fourcc, FPS, (cntr * 2).to_int())


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


def rotateToColor(color, speed=20, reverse=False, duo=0):
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


try:
    while True:
        # Переменные для хранения лучшего (самого большого) контура
        best_area = 0
        best_index = -1
        best_contours = None
        best_raw = None

        # Проходим по всем цветам в очереди
        for i, col in enumerate(queue):
            contours, raw = getContoursColor(col)
            if contours:
                area = cv2.contourArea(contours[0])
                if area > best_area:
                    best_area = area
                    best_index = i
                    best_contours = contours
                    best_raw = raw

        # Если ни одного контура не найдено – вращаемся на месте
        if best_index == -1:
            speed = 20
            reverse = False
            motor_left.set_motor(speed * ((2 * int(reverse)) - 1))
            motor_right.set_motor(speed * ((-2 * int(reverse)) + 1))
            continue

        # Выбранный цвет и его контуры
        color_max = queue[best_index]
        contours_color_max = best_contours
        c_area = best_area
        print('c_area', c_area)
        print(queue_name[best_index])
        # raw = best_raw  # можно использовать для отладки или записи видео
        [173, 524]
        [374, 313]

        [498, 277]
        [728, 388]
        # Если площадь достаточно велика, начинаем управление
        if c_area > 1000:
            if color_max['stop_area'] > c_area:
                # Берём первый (самый большой) контур
                largest_contour = contours_color_max[0]
                min_y_point_contour = max(largest_contour, key=lambda point: point[0].tolist()[1])[0].tolist()
                print(min_y_point_contour)
                color_cntr = getCenter(largest_contour)
                cv2.circle(best_raw, min_y_point_contour, 10, (0, 0, 0), -1)
                out.write(
                    cv2.drawContours(cv2.cvtColor(best_raw, cv2.COLOR_BGR2RGB), contours_color_max, -1, (255, 0, 0), -1))
                delta_x = (cntr - color_cntr).x
                u = PID_yaw(delta_x)
                u_speed = PID_speed(c_area)
                print('u_speed', u_speed)
                print('u', u)
                print('delta_x', delta_x)
                # motor_left.set_motor(u_speed - u)
                # motor_right.set_motor(u_speed + u)
                # out.release()
                # exit(0)
            else:
                # Достигли нужной близости к цели – удаляем цвет из очереди и выходим

                queue.pop(best_index)
                if len(queue) == 0:
                    break
        else:
            # Если площадь мала (менее 500) – тоже вращаемся
            speed = 20
            reverse = False
            # motor_left.set_motor(speed * ((2 * int(reverse)) - 1))
            # motor_right.set_motor(speed * ((-2 * int(reverse)) + 1))
except Exception as e:
    print("Произошла ошибка:")
    traceback.print_exc()

out.release()

