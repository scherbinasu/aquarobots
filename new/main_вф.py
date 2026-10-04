import colors, time
import datetime
import traceback
import numpy as np
import cv2
from robot.findMask import *
from robot.robot import AquaRobot
from control.web.webGUI import WebGUI
import RPi.GPIO as GPIO
import robot.findOpenCV as findOpenCV


# =========================================================
#                    ЛОГИРОВАНИЕ
# =========================================================
def log(msg, level="INFO"):
    t = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if level == "STEP": print('\n')
    print(f"[{t}] [{level}] {msg}", flush=True)
    if level == "STEP": print('\n')


# =========================================================
#                ЦВЕТА ДЛЯ ОТРИСОВКИ (BGR)
# =========================================================
BGR_RED     = (0, 0, 255)
BGR_GREEN   = (0, 255, 0)
BGR_YELLOW  = (0, 255, 255)
BGR_ORANGE  = (0, 165, 255)
BGR_WHITE   = (255, 255, 255)
BGR_BLACK   = (0, 0, 0)
BGR_GRAY    = (110, 110, 110)
BGR_CYAN    = (255, 255, 0)
BGR_MAGENTA = (255, 0, 255)

COLOR_BGR = {
    "Red":    BGR_RED,
    "Green":  BGR_GREEN,
    "Yellow": BGR_YELLOW,
    "Orange": BGR_ORANGE,
}


# =========================================================
#                        FPS-МЕТР
# =========================================================
class FPSMeter:
    def __init__(self, window=30):
        self.times = []
        self.window = window

    def tick(self):
        now = time.time()
        self.times.append(now)
        if len(self.times) > self.window:
            self.times.pop(0)
        if len(self.times) < 2:
            return 0.0
        return (len(self.times) - 1) / (self.times[-1] - self.times[0])


_fps = FPSMeter()


# =========================================================
#                  ХЕЛПЕРЫ ОТРИСОВКИ
# =========================================================
def safe_center(obj):
    """Возвращает Point центра или None (если момент нулевой/объект не тот)."""
    if obj is None:
        return None
    try:
        c = obj.getCenter()
    except Exception:
        traceback.print_exc()
        return None
    return c


def draw_crosshair(frame, color=BGR_GRAY):
    h, w = frame.shape[:2]
    cv2.line(frame, (w // 2, 0), (w // 2, h), color, 1)
    cv2.line(frame, (0, h // 2), (w, h // 2), color, 1)
    cv2.rectangle(frame, (w // 2 - 20, h // 2 - 20),
                  (w // 2 + 20, h // 2 + 20), color, 1)


def overlay_contours(frame, contours, color_bgr, alpha=0.35, thickness=2,
                     show_labels=True, prefix=""):
    """Полупрозрачная заливка + обводка + подписи (индекс, площадь) + центры."""
    if not contours:
        return frame
    try:
        raw = [c.contour for c in contours]
    except AttributeError:
        return frame
    overlay = frame.copy()
    cv2.drawContours(overlay, raw, -1, color_bgr, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.drawContours(frame, raw, -1, color_bgr, thickness)

    if show_labels:
        for i, c in enumerate(contours):
            cntr = safe_center(c)
            if cntr is None:
                continue
            x, y = cntr.to_int()
            cv2.circle(frame, (x, y), 4, BGR_WHITE, -1)
            cv2.circle(frame, (x, y), 4, color_bgr, 1)
            try:
                area = c.getArea()
            except Exception:
                area = 0
            txt = f"{prefix}#{i} A={area:.0f}"
            cv2.putText(frame, txt, (x + 8, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, BGR_BLACK, 3, cv2.LINE_AA)
            cv2.putText(frame, txt, (x + 8, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, BGR_WHITE, 1, cv2.LINE_AA)
    return frame


def draw_info_panel(frame, lines, origin=(10, 10), line_h=20, panel_w=470,
                    font_scale=0.5, alpha=0.55):
    """Полупрозрачная панель с текстом в левом верхнем углу."""
    x, y = origin
    panel_h = len(lines) * line_h + 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + panel_w, y + panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (110, 110, 110), 1)
    for i, item in enumerate(lines):
        if isinstance(item, tuple) and len(item) == 2:
            text, color = item
        else:
            text, color = str(item), BGR_WHITE
        ty = y + 18 + i * line_h
        cv2.putText(frame, text, (x + 10, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, BGR_BLACK, 3, cv2.LINE_AA)
        cv2.putText(frame, text, (x + 10, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1, cv2.LINE_AA)
    return frame


def queue_status_str(queue_name, done_indices):
    parts = []
    for i, name in enumerate(queue_name):
        parts.append(f"[v {name}]" if i in done_indices else f"[  {name}]")
    return " ".join(parts)


def show_raw(frame, lines=None, note=""):
    """Панель + отправка в веб-интерфейс + запись в видео."""
    fps = _fps.tick()
    all_lines = [(f"FPS: {fps:5.1f}", BGR_CYAN)]
    if lines:
        all_lines.extend(lines)
    draw_info_panel(frame, all_lines)
    aquaRobot.gui.imshow("raw", frame)
    if aquaRobot.video is not None:
        aquaRobot.video.write(frame)
    if note:
        log(f"raw -> web+video | {note}", "INFO")


# =========================================================
#                    ДЕТЕКТОР ОБЪЕКТА
# =========================================================
def findObj(frame, paramsObj):
    try:
        lower = (int(paramsObj['h_min']), int(paramsObj['s_min']), int(paramsObj['v_min']))
        upper = (int(paramsObj['h_max']), int(paramsObj['s_max']), int(paramsObj['v_max']))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame[:, :, 0] += paramsObj['addH']
        frame[:, :, 0] %= 180
        if paramsObj['blur'] > 0:
            frame = cv2.GaussianBlur(frame, (0, 0),
                                     sigmaX=paramsObj['blur'] / 50,
                                     sigmaY=paramsObj['blur'] / 50)
        masked = cv2.inRange(frame, lower, upper)
        obrez = int(paramsObj['obrez'])
        if obrez > 0:
            masked[:obrez, :] = 0

        masked = findOpenCV.FindMask(masked)
        c = masked.findContours()
        c = list(filter(lambda x: paramsObj['com_max'] / 100 >= x.compactness() >= paramsObj['com_min'] / 100, c))
        c = list(filter(lambda x: paramsObj['nu2_max'] / 100 >= x.moment()['nu20'] >= paramsObj['nu2_min'] / 100, c))
        c = sorted(c, key=lambda x: x.getArea(), reverse=True)
        return masked, c
    except Exception as e:
        log(f"Ошибка в findObj: {e}", "ERROR")
        traceback.print_exc()
        return None, []


# =========================================================
#                          MAIN
# =========================================================
try:
    log("=== Старт программы ===", "STEP")
    log(f"OpenCV: {cv2.__version__}", "INFO")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN)
    log(f"GPIO BCM инициализирован, вход 4 = {GPIO.input(4)}", "INFO")

    log("Создание AquaRobot...", "INFO")
    aquaRobot = AquaRobot()
    log("Запуск AquaRobot (камера + моторы + веб-интерфейс)...", "INFO")
    aquaRobot.start(cv2=cv2, FPS=5)
    log("AquaRobot запущен успешно", "OK")

    Red    = colors.Red
    Green  = colors.Green
    Yellow = colors.Yellow
    Orange = colors.Orange
    log("Цвета загружены: Red, Green, Yellow, Orange", "INFO")

    del_index_color = []
    queue = [Yellow, Green, Red]
    all_color = [Yellow, Green, Red]
    queue_name = ['Yellow', 'Green', 'Red']

    PID_yaw_port   = PID_regulator(-0.04, 0, 0, 0)
    PID_speed_port = PID_regulator(0.0004, 0, 0, 90000)
    PID_yaw_gate   = PID_regulator(-0.08, 0, 0, 0)
    PID_speed_gate = PID_regulator(0.0004, 0, 0, 90000)
    log("PID-регуляторы: port(yaw, speed), gate(yaw, speed)", "INFO")

    # ---------- Ожидание кнопки ----------
    log("Ожидание кнопки GPIO 4...", "STEP")
    while True:
        if not GPIO.input(4):
            log("Кнопка сработала — старт", "OK")
            break
        else:
            log("Ждём кнопку...", "INFO")
            time.sleep(0.01)

    # ---------- ЭТАП 1: поворот к воротам ----------
    log("=== ЭТАП 1: поворот к воротам ===", "STEP")
    while True:
        img = aquaRobot.camera.get_frame()
        mask, contours = findObj(img, Orange)

        vis = img.copy()
        draw_crosshair(vis, BGR_GRAY)
        if contours:
            overlay_contours(vis, contours[:2], BGR_ORANGE, alpha=0.4, thickness=2)

        lines = [
            ("ЭТАП 1: поворот к воротам", BGR_YELLOW),
            (f"Контуров: {len(contours)}", BGR_WHITE),
        ]
        if len(contours) >= 1:
            lines.append((f"#0 A={contours[0].getArea():.0f}", BGR_ORANGE))
        if len(contours) >= 2:
            lines.append((f"#1 A={contours[1].getArea():.0f}", BGR_ORANGE))

        show_raw(vis, lines, f"stage1 contours={len(contours)}")
        if mask is not None:
            aquaRobot.gui.imshow("mask", mask.mask)

        if len(contours) >= 2 and contours[1].getArea() > 500:
            log(f"Ворота найдены: #1 A={contours[1].getArea():.1f} — стоп", "OK")
            aquaRobot.motor_left.set_motor(0)
            aquaRobot.motor_right.set_motor(0)
            break
        if len(contours) == 1:
            log("Найден 1 контур ворот, продолжаем поиск", "INFO")
        aquaRobot.motor_left.set_motor(30 * ((2 * int(False)) - 1))
        aquaRobot.motor_right.set_motor(30 * ((-2 * int(False)) + 1))

    # ---------- ЭТАП 2: проезд через ворота ----------
    log("=== ЭТАП 2: проезд через ворота ===", "STEP")
    while True:
        img = aquaRobot.camera.get_frame()
        mask, c = findObj(img, Orange)

        vis = img.copy()
        draw_crosshair(vis, BGR_GRAY)
        if c:
            overlay_contours(vis, c[:2], BGR_ORANGE, alpha=0.4, thickness=2)

        lines = [
            ("ЭТАП 2: проезд через ворота", BGR_YELLOW),
            (f"Контуров: {len(c)}", BGR_WHITE),
        ]

        if len(c) >= 2 and c[1].getArea() > 500:
            orange_cntr   = FindMask(contours=[c[0].contour]).getCenter()[0]
            orange_cntr_2 = FindMask(contours=[c[1].contour]).getCenter()[0]
            cv2.circle(vis, orange_cntr.to_int(),   6, BGR_GREEN, 2)
            cv2.circle(vis, orange_cntr_2.to_int(), 6, BGR_RED, 2)
            mid = (orange_cntr + orange_cntr_2) / 2
            cv2.circle(vis, mid.to_int(), 6, BGR_YELLOW, 2)
            cv2.line(vis, orange_cntr.to_int(), orange_cntr_2.to_int(), BGR_YELLOW, 1)

            delta_x_yaw   = (mask.getCenter() - mid).x
            delta_x_speed = abs((orange_cntr - orange_cntr_2).x)
            u       = PID_yaw_gate(delta_x_yaw * 2)
            u_speed = PID_speed_gate(delta_x_speed)

            lines += [
                (f"#0 A={c[0].getArea():.0f} C={orange_cntr.to_int()}", BGR_GREEN),
                (f"#1 A={c[1].getArea():.0f} C={orange_cntr_2.to_int()}", BGR_RED),
                (f"Mid = {mid.to_int()}", BGR_YELLOW),
                (f"d_yaw={delta_x_yaw:.2f}  d_speed={delta_x_speed:.2f}", BGR_WHITE),
                (f"u={u:.3f}  u_speed={u_speed:.3f}", BGR_CYAN),
                (f"L={u_speed - u:.1f}  R={u_speed + u:.1f}", BGR_MAGENTA),
            ]

            show_raw(vis, lines, f"stage2 gates area={c[1].getArea():.0f}")
            if mask is not None:
                aquaRobot.gui.imshow("mask", mask.mask)

            log(f"Ворота: d_yaw={delta_x_yaw:.2f} d_speed={delta_x_speed:.2f} "
                f"u={u:.3f} u_speed={u_speed:.3f}", "INFO")
            aquaRobot.motor_left.set_motor(u_speed - u)
            aquaRobot.motor_right.set_motor(u_speed + u)
            log(f"Моторы: L={u_speed - u:.1f}  R={u_speed + u:.1f}", "INFO")
        else:
            show_raw(vis, lines, f"stage2 contours={len(c)}")
            if mask is not None:
                aquaRobot.gui.imshow("mask", mask.mask)
            log("Ворота пройдены/потеряны — остановка, выход", "OK")
            aquaRobot.sleepV(2)
            aquaRobot.motor_left.set_motor(0)
            aquaRobot.motor_right.set_motor(0)
            break

    # ---------- ЭТАП 3: буйки x
    log("=== ЭТАП 3: проезд по буйкам ===", "STEP")
    while True:
        best_area = 0
        best_index = -1
        best_contours = None
        best_raw = None
        best_color_cntr = None
        u = 0  # страховка от NameError в ветке «reached»

        for i, col in enumerate(queue):
            if i not in del_index_color:
                img = aquaRobot.camera.get_frame()
                mask, contours = findObj(img, col)
                if contours:
                    area = contours[0].getArea()
                    log(f"Кандидат [{queue_name[i]}]: A={area:.1f}", "INFO")
                    if area > best_area:
                        best_area = area
                        best_index = i
                        best_contours = contours
                        best_raw = img
                        best_color_cntr = FindMask(contours=[contours[0].contour]).getCenter()[0]

        if best_index != -1:
            contours_color_max = best_contours
            c_area = best_area
            log(f"Выбран {queue_name[best_index]} A={c_area:.1f}", "OK")
        else:
            c_area = 0
            log("Ничего не найдено — вращение", "WARN")

        if c_area > 500:
            largest_contour = contours_color_max[0].contour
            min_y_point_contour = max(largest_contour, key=lambda p: p[0].tolist()[1])[0].tolist()[1]
            color_cntr = FindMask(contours=[largest_contour]).getCenter()[0]

            vis = best_raw.copy()
            draw_crosshair(vis, BGR_GRAY)
            target_bgr = COLOR_BGR.get(queue_name[best_index], BGR_ORANGE)
            overlay_contours(vis, contours_color_max, target_bgr, alpha=0.45, thickness=3)

            # линия top_y
            cv2.line(vis, (0, min_y_point_contour),
                     (vis.shape[1], min_y_point_contour), BGR_CYAN, 2)
            cv2.putText(vis, f"top_y={min_y_point_contour}",
                        (10, min_y_point_contour - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, BGR_CYAN, 2, cv2.LINE_AA)

            frame_center = mask.getCenter()
            threshold = frame_center.y * 2 - 5 if frame_center else 480

            # пороговая линия
            cv2.line(vis, (0, int(threshold)),
                     (vis.shape[1], int(threshold)), BGR_MAGENTA, 2)
            cv2.putText(vis, f"thr_y={threshold:.0f}",
                        (vis.shape[1] - 170, int(threshold) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, BGR_MAGENTA, 2, cv2.LINE_AA)

            lines = [
                ("ЭТАП 3: проезд по буйкам", BGR_YELLOW),
                (f"Очередь: {queue_status_str(queue_name, del_index_color)}", BGR_WHITE),
                (f"Цель: {queue_name[best_index]}", target_bgr),
                (f"Лучшая A={c_area:.0f}  C={color_cntr.to_int()}", BGR_WHITE),
                (f"top_y={min_y_point_contour}  thr={threshold:.0f}", BGR_CYAN),
            ]

            if min_y_point_contour <= threshold:
                delta_x = (frame_center - color_cntr).x if frame_center else 0
                u       = PID_yaw_port(delta_x)
                u_speed = PID_speed_port(c_area)

                lines += [
                    (f"delta_x={delta_x:.2f}", BGR_WHITE),
                    (f"u={u:.3f}  u_speed={u_speed:.3f}", BGR_CYAN),
                    (f"L={u_speed - u:.1f}  R={u_speed + u:.1f}", BGR_MAGENTA),
                ]

                show_raw(vis, lines,
                         f"stage3 target={queue_name[best_index]} approach")
                if mask is not None:
                    aquaRobot.gui.imshow("mask", mask.mask)

                log(f"Подход к {queue_name[best_index]}: d_x={delta_x:.2f} "
                    f"u={u:.3f} u_speed={u_speed:.3f}", "INFO")
                aquaRobot.motor_left.set_motor(u_speed - u)
                aquaRobot.motor_right.set_motor(u_speed + u)
                log(f"Моторы: L={u_speed - u:.1f}  R={u_speed + u:.1f}", "INFO")
            else:
                lines.append((f"{queue_name[best_index]} ДОСТИГНУТ", BGR_GREEN))
                show_raw(vis, lines,
                         f"stage3 target={queue_name[best_index]} reached")
                if mask is not None:
                    aquaRobot.gui.imshow("mask", mask.mask)

                log(f"{queue_name[best_index]} достигнут, откат", "OK")
                aquaRobot.motor_left.set_motor(20)
                aquaRobot.motor_right.set_motor(20)
                aquaRobot.sleepV(2)
                del_index_color.append(best_index)
                aquaRobot.motor_left.set_motor(-35 + u * 3)
                aquaRobot.motor_right.set_motor(-35 - u * 3)
                log(f"PID интегралы: speed={PID_speed_port.integral_err:.3f} "
                    f"yaw={PID_yaw_port.integral_err:.3f}", "INFO")
                if len(del_index_color) == 3:
                    log("Все буйки пройдены! Пауза 1 с", "OK")
                    aquaRobot.sleepV(1)
                else:
                    log(f"Пройдено {len(del_index_color)}/3, пауза 3 с", "INFO")
                    aquaRobot.sleepV(3)
                aquaRobot.motor_left.set_motor(0)
                aquaRobot.motor_right.set_motor(0)
                if len(del_index_color) == 3:
                    log("=== ЭТАП 3 завершён ===", "STEP")
                    break
        else:
            speed = 25
            reverse = -1 if PID_yaw_port.integral_err <= 0 else 1
            L = speed * ((2 * int(reverse)) - 1)
            R = speed * ((-2 * int(reverse)) + 1)
            aquaRobot.motor_left.set_motor(L)
            aquaRobot.motor_right.set_motor(R)

            # Показываем "сырой" кадр даже при поиске
            img_dbg = aquaRobot.camera.get_frame()
            vis = img_dbg.copy()
            draw_crosshair(vis, BGR_GRAY)
            lines = [
                ("ЭТАП 3: поиск (вращение)", BGR_YELLOW),
                (f"Очередь: {queue_status_str(queue_name, del_index_color)}", BGR_WHITE),
                (f"direction={reverse}  L={L}  R={R}", BGR_MAGENTA),
            ]
            show_raw(vis, lines, "stage3 search")
            log(f"Поиск: dir={reverse} L={L} R={R}", "INFO")

    log("=== Всё завершено, отключаюсь ===", "STEP")
    aquaRobot.gui.destroyAllWindows()
    log("Веб-интерфейс остановлен", "OK")

except Exception as e:
    log(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", "ERROR")
    traceback.print_exc()
    aquaRobot.stop()