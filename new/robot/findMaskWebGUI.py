import os

import cv2
from control.camera.camera import HardCamera
from findMask import *
from control.web.webGUI import WebGUI
import json




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
            PRESETS[str(i+1)] = json.loads("{"+line+"}")
    return PRESETS

# ---- 4 пресета (маски). Ключи должны совпадать с col ----
PRESETS = parse_python_lib_color()
print(PRESETS)
def main():
    cap = HardCamera(size=(820, 616))
    cap.start()

    gui = WebGUI(host='0.0.0.0', port=5000)

    # Рабочая копия параметров активного пресета — мутируется на месте.
    current_slot = ["1"]
    col = dict(PRESETS[current_slot[0]])

    KEYS = ["h_min", "h_max", "s_min", "s_max", "v_min", "v_max", "obrez"]
    LABELS = {
        "h_min": "H Min", "h_max": "H Max",
        "s_min": "S Min", "s_max": "S Max",
        "v_min": "V Min", "v_max": "V Max",
        "obrez": "Obrez",
    }
    MAXS = {
        "h_min": 180, "h_max": 180,
        "s_min": 255, "s_max": 255,
        "v_min": 255, "v_max": 255,
        "obrez": 480,
    }

    # Регистрируем слайдеры
    for key in KEYS:
        def make_cb(k):
            def cb(val):
                col[k] = int(val)
            return cb
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

        mask = FindMask(frame)
        mask.inRangeF(col)

        corners, ids, _ = detector.detectMarkers(frame)
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        gui.imshow("raw", frame)
        gui.imshow("masked", mask.frame)

        if gui.waitKey(30) == ord('q'):
            break

    cap.release()
    gui.destroyAllWindows()


if __name__ == '__main__':
    main()