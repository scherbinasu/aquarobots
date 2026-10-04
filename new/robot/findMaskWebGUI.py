import os, traceback

import cv2
from control.camera.camera import HardCamera
from findMask import *
from control.web.webGUI import WebGUI
import json
import findOpenCV as findOpenCV


def save_python_lib_color(presets):
    with open('/home/ubuntu/aquarobots/new/colors.py', "w") as f:
        data = f'''
Red = {presets['1']}
Green = {presets['2']}
Yellow = {presets['3']}
Orange = {presets['4']}
        '''
        f.write(data)


def parse_python_lib_color():
    PRESETS = {}
    with open('/home/ubuntu/aquarobots/new/colors.py', 'r') as f:
        data = f.read()
        print(data)
        data = data.split('{')
        for i, line in enumerate(data[1:]):
            line = line.split('}')[0].replace("'", '"')
            PRESETS[str(i + 1)] = json.loads("{" + line + "}")
    return PRESETS


# ---- 4 пресета (маски). Ключи должны совпадать с col ----
PRESETS = parse_python_lib_color()
print(PRESETS)
def findObj(frame, paramsObj):
    try:
        lower = (int(paramsObj['h_min']), int(paramsObj['s_min']), int(paramsObj['v_min']))
        upper = (int(paramsObj['h_max']), int(paramsObj['s_max']), int(paramsObj['v_max']))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame[:, :, 0] += paramsObj['addH']
        frame[:, :, 0] %= 180
        if paramsObj['blur'] > 0:
            frame = cv2.GaussianBlur(frame, (0, 0), sigmaX=paramsObj['blur'] / 50, sigmaY=paramsObj['blur'] / 50)
        masked = cv2.inRange(frame, lower, upper)
        obrez = int(paramsObj['obrez'])
        if obrez > 0:
            masked[:obrez, :] = 0

        masked = findOpenCV.FindMask(masked)
        c = masked.findContours()
        c = list(filter(lambda x: paramsObj['com_max'] / 100 >= x.compactness() >= paramsObj['com_min'] / 100, c))
        c = list(filter(lambda x: paramsObj['nu2_max'] / 100 >= x.moment()['nu20'] >= paramsObj['nu2_min'] / 100, c))
        c = sorted(c, key=lambda x: x.getArea(), reverse=True)
        return frame, c, masked, (c[0] if c else None)
    except Exception:
        traceback.print_exc()
        return [], None, None

def main():
    cap = HardCamera(size=(820, 616))
    cap.start()

    gui = WebGUI(host='0.0.0.0', port=5000)

    # Рабочая копия параметров активного пресета — мутируется на месте.
    current_slot = ["1"]
    col = dict(PRESETS[current_slot[0]])

    KEYS = ["h_min", "h_max", "s_min", "s_max", "v_min", "v_max", 'com_min', 'com_max', 'nu2_min', 'nu2_max', "obrez", "addH", 'blur']
    LABELS = {
        "h_min": "H Min", "h_max": "H Max",
        "s_min": "S Min", "s_max": "S Max",
        "v_min": "V Min", "v_max": "V Max",
        'com_min': "Com Min",'com_max': "Com Max",
        'nu2_min': "nu2 Min",'nu2_max': "nu2 Mas",
        "obrez": "Obrez", "addH" : "add Hue", 'blur': 'Blur'
    }
    MAXS = {
        "h_min": 180, "h_max": 180,
        "s_min": 255, "s_max": 255,
        "v_min": 255, "v_max": 255,
        'com_min':100, 'com_max':100,
        'nu2_min':100, 'nu2_max':100,
        "obrez": 480, "addH": 180,
        "blur": 500
    }

    # Регистрируем слайдеры
    for key in KEYS:
        def make_cb(k):
            def cb(val):
                col[k] = int(val)

            return cb
        print(key)
        gui.createTrackbar(key, "control", col[key], MAXS[key],
                           make_cb(key), label=LABELS[key])

    # ---- переключение пресета ----
    def load_slot(slot_key):
        current_slot[0] = str(slot_key)
        col.clear()
        col.update(PRESETS[current_slot[0]])
        # Обновить слайдеры в UI
        for k in KEYS:
            gui.setTrackbarPos(k, col[k])

    # ---- сохранение в активный пресет ----
    def save_slot():
        PRESETS[current_slot[0]] = dict(col)
        save_python_lib_color(PRESETS)
        print(f"[preset {current_slot[0]}] saved -> {PRESETS[current_slot[0]]}")

    gui.setPresets(
        options={"1": "Red", "2": "Green", "3": "Yellow", "4": "Orange"},
        value=current_slot[0],
        callback=load_slot,
    )
    gui.onSave(save_slot)

    # ---- ArUco ----
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    gui.start()
    print("Сервер запущен. Откройте в браузере: http://<IP-адрес>:5000")

    while True:
        frame = cap.get_frame()
        if frame is None:
            continue

        frame, m1, m2, m3 = findObj(frame, col)

        corners, ids, _ = detector.detectMarkers(frame)
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        gui.imshow("raw", frame)

        # m1 — список FindContour -> извлекаем "сырые" cv2-контуры
        canvas = np.zeros(frame.shape[:2], dtype=np.uint8)
        if isinstance(m1, list) and m1:
            cv2.drawContours(canvas, [c.contour for c in m1], -1, 255, -1)
        gui.imshow("masked", canvas)

        # m2 — объект FindMask -> берём .mask
        if hasattr(m2, "mask"):
            gui.imshow("masked2", m2.mask)

        # m3 — объект FindContour -> рисуем через genImg
        if hasattr(m3, "genImg"):
            gui.imshow("masked3", m3.genImg(frame.shape))

        if gui.waitKey(30) == ord('q'):
            break

    cap.release()
    gui.destroyAllWindows()


if __name__ == '__main__':
    main()
