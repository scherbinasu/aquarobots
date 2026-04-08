import traceback
import cv2
import time
from hard_control.abstractions import *

if __name__ == '__main__':
    from hard_control.hard_camera import *
    from hard_control.hard_motors import *

    cam = HardCamera()
    motor_left = HardMotor(pwm_channel=PWM_CHANNEL_2, hz=PWM_FREQ, chip=PWM_CHIP)
    motor_right = HardMotor(pwm_channel=PWM_CHANNEL_1, hz=PWM_FREQ, chip=PWM_CHIP)
    time.sleep(3)
else:
    import cv2, time
if __name__ == '__main__':
    Yellow = {"obrez": "170", "h_min": "87", "s_min": "92", "s_max": "255", "v_min": "179", "v_max": "255", "h_max": "99"}
    Green = {"obrez": "170", "h_min": "60", "s_min": "127", "s_max": "255", "v_min": "102", "v_max": "255", "h_max": "84"}
    Red = {"obrez": "170", "h_min": "120", "s_min": "84", "s_max": "255", "v_min": "73", "v_max": "255", "h_max": "180"}
    Orange = {"obrez": "170", "h_min": "101", "s_min": "197", "s_max": "255", "v_min": "174", "v_max": "255",
          "h_max": "116"}
else:
    import colors
    Yellow = colors.Yellow
    Green = colors.Green
    Red = colors.Red
    Orange = colors.Orange
del_index_color = []
queue = [Yellow, Green, Red]
all_color = [Yellow, Green, Red]
queue_name = ['Yellow', 'Green', 'Red']
min_y_point_contour = 0
# PID_yaw = PID_regulator(-0.055, -0.01, 0, 0)
# PID_speed = PID_regulator(0.00045, -0.0001, 0, 120000)
PID_yaw = PID_regulator(-0.06, 0, 0, 0)
PID_speed = PID_regulator(0.00035, 0, 0, 120000)
def video_sleep(sleep_time, out, FPS, get_img):
    time_start = time.time()
    while time_start+sleep_time > time.time():
        time.sleep(1 / FPS)
        out.write(get_img())
if __name__ == '__main__':
    cntr = Point(cam.get_frame().shape[1::-1]) / 2
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


def getContoursColor(color, func_get_img=None):
    if func_get_img is None:
        raw = cam.get_frame()
    else:
        raw = func_get_img()
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

def run_go_to_ports(motor_left, motor_right, func_get_img=None, out_video=None, fps=30):
    video_sleep(2, out_video, fps, func_get_img)
    try:
        cntr = Point(func_get_img().shape[1::-1]) / 2
        while True:
            # Переменные для хранения лучшего (самого большого) контура
            best_area = 0
            best_index = -1
            best_contours = None
            best_raw = None

            # Проходим по всем цветам в очереди
            for i, col in enumerate(queue):
                if not i in del_index_color:
                    contours, raw = getContoursColor(col, func_get_img)
                    if contours:
                        area = cv2.contourArea(contours[0])
                        if area > best_area:
                            best_area = area
                            best_index = i
                            best_contours = contours
                            best_raw = raw
                            best_color_cntr = getCenter(contours[0])

            if best_index != -1:

                color_max = queue[best_index]
                contours_color_max = best_contours
                c_area = best_area
                print(queue_name[best_index])
                if 0:
                    for i, col in enumerate(queue):
                        if best_index != i:
                            contours, raw = getContoursColor(col, func_get_img)
                            if contours:
                                area = cv2.contourArea(contours[0])
                                if area > 500:
                                    color_cntr = getCenter(contours[0])
                                    if color_cntr is not None:
                                        asdg = best_color_cntr - color_cntr
                                        print(asdg, queue_name[i])
                                        if abs(asdg.x) < 30:
                                            c_area = 0
                # Выбранный цвет и его контуры

                # print('c_area', c_area)
                # print(queue_name[best_index])
                # raw = best_raw  # можно использовать для отладки или записи видео
                # Если площадь достаточно велика, начинаем управление
            else:
                c_area = 0
            if c_area > 500:

                # Берём первый (самый большой) контур
                largest_contour = contours_color_max[0]
                min_y_point_contour = max(largest_contour, key=lambda point: point[0].tolist()[1])[0].tolist()[1]
                # print(min_y_point_contour)
                color_cntr = getCenter(largest_contour)
                cv2.line(best_raw, (0, min_y_point_contour), (820, min_y_point_contour), (0, 0, 0), 3)
                best_raw = cv2.putText(best_raw, str(min_y_point_contour), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                       (255, 0, 0), 2)
                out_video.write(
                    cv2.drawContours(cv2.cvtColor(best_raw, cv2.COLOR_BGR2RGB), contours_color_max, -1, (255, 0, 0), -1))
                # print(cntr.y * 2 - 5)
                if min_y_point_contour <= cntr.y * 2 - 5:
                    delta_x = (cntr - color_cntr).x
                    u = PID_yaw(delta_x)
                    u_speed = PID_speed(c_area)
                    # print('u_speed', u_speed)
                    # print('u', u)
                    # print('delta_x', delta_x)
                    motor_left.set_motor(u_speed - u)
                    motor_right.set_motor(u_speed + u)
                    print(u_speed - u, 'motor')
                    print(u_speed + u, 'motor')
                    # out.release()
                    # exit(0)
                else:
                    video_sleep(2, out_video, fps, func_get_img)
                    # Достигли нужной близости к цели – удаляем цвет из очереди и выходим
                    del_index_color.append(best_index)
                    # queue.pop(best_index)
                    motor_left.set_motor(-35 +  u*3)
                    motor_right.set_motor(-35 - u*3)
                    print(PID_speed.integral_err)
                    print(PID_yaw.integral_err)
                    if len(del_index_color) == 3:video_sleep(1, out_video, fps, func_get_img)
                    else:video_sleep(3, out_video, fps, func_get_img)
                    motor_left.set_motor(0)
                    motor_right.set_motor(0)
                    if len(del_index_color) == 3:
                        break
            else:
                # Если площадь мала (менее 500) – тоже вращаемся
                speed = 25
                reverse = -1 if PID_yaw.integral_err <= 0 else 1
                motor_left.set_motor(speed * ((2 * int(reverse)) - 1))
                motor_right.set_motor(speed * ((-2 * int(reverse)) + 1))
    except:
        print("Произошла ошибка:")
        traceback.print_exc()


if __name__ == '__main__':
    try:
        run_go_to_ports(motor_left, motor_right, cam.get_frame, out)
    except:
        traceback.print_exc()
    motor_left.set_motor(0)
    motor_right.set_motor(0)
    cam.release()
    out.release()
