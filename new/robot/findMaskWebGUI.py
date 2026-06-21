import cv2
from control.camera.camera import HardCamera
from findMask import *
from control.web.webGUI import WebGUI

def main():
    # 1. Камера
    cap = HardCamera(size=(820, 616))
    cap.start()

    # 2. Веб-интерфейс
    gui = WebGUI(host='0.0.0.0', port=5000)

    # 3. Параметры HSV
    col = {"obrez": "0", "h_min": "0", "s_min": "0", "s_max": "255", "v_min": "0", "v_max": "255", "h_max": "255"}
    col = {"obrez": "190", "h_min": "8", "s_min": "184", "s_max": "255", "v_min": "41", "v_max": "255", "h_max": "30"}

    # 4. Колбэки для трекбаров
    def on_h_min(val): col["h_min"] = val
    def on_h_max(val): col["h_max"] = val
    def on_s_min(val): col["s_min"] = val
    def on_s_max(val): col["s_max"] = val
    def on_v_min(val): col["v_min"] = val
    def on_v_max(val): col["v_max"] = val
    def on_obrez(val): col["obrez"] = val

    # Создаём трекбары
    gui.createTrackbar("H Min", "control", 0, 180, on_h_min)
    gui.createTrackbar("H Max", "control", 180, 180, on_h_max)
    gui.createTrackbar("S Min", "control", 0, 255, on_s_min)
    gui.createTrackbar("S Max", "control", 255, 255, on_s_max)
    gui.createTrackbar("V Min", "control", 0, 255, on_v_min)
    gui.createTrackbar("V Max", "control", 255, 255, on_v_max)
    gui.createTrackbar("Obrez", "control", 0, 480, on_obrez)

    # 5. Детектор ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)
    gui.start()
    print("Сервер запущен. Откройте в браузере: http://<IP-адрес>:5000")

    while True:
        frame = cap.get_frame()      # BGR
        if frame is None:
            continue

        # Создаём маску
        mask = FindMask(frame)
        # mask.normalize()
        mask.inRangeF(col)

        # Детекция ArUco на исходном кадре
        corners, ids, _ = detector.detectMarkers(frame)
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        # Отображаем два окна
        gui.imshow("raw", frame)          # окно с именем "raw"
        gui.imshow("masked", mask.frame)        # окно с именем "masked"

        # Задержка для управления частотой кадров (имитация waitKey)
        if gui.waitKey(30) == ord('q'):   # всегда -1, но оставляем для совместимости
            break

    cap.release()
    gui.destroyAllWindows()

if __name__ == '__main__':
    main()