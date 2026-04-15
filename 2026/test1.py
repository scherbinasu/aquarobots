from bestMaskMetod import *
import numpy as np
import cv2

path_video = r"C:\Users\user\Desktop\output.mp4"
cap = cv2.VideoCapture(path_video)

def fill_ceiling_above_walls(mask_walls, original_image):
    # mask_walls - одноканальная бинарная маска (0 или 255)
    h, w = mask_walls.shape
    ceiling_mask = np.zeros((h, w), dtype=np.uint8)

    for x in range(w):
        col = mask_walls[:, x]
        ys = np.where(col > 0)[0]
        if len(ys) > 0:
            top_y = ys.min()
            ceiling_mask[:top_y, x] = 255
        # иначе ничего не делаем (потолок не закрашиваем)

    result = original_image.copy()
    result[ceiling_mask == 255] = (255, 255, 255)
    return result
ret, frame = cap.read()
cntr = Point(frame.shape[1::-1])/2
OUTPUT_FILE = "output.mp4"      # имя выходного файла
FPS = 30*0.2                         # кадров в секунду
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # кодек для MP4
out = cv2.VideoWriter(OUTPUT_FILE, fourcc, FPS, (2460, 616))
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = normalize(frame)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    bw = cv2.inRange(hsv, (100, 30, 30), (140, 255, 180))
    contours, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Создаём одноканальную маску для трёх самых больших контуров
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    for cnt in contours[:3]:
        approx_cnt = approx(cnt, 0.015)  # очень слабая аппроксимация
        cv2.drawContours(mask, [approx_cnt], -1, 255, -1)

    f = fill_ceiling_above_walls(mask, frame)

    cv2.imshow('frame', frame)
    cv2.imshow('bw', mask)
    cv2.imshow('contours', f)

    # Приводим bw к трём каналам для hstack
    bw_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    combined = np.hstack((frame, bw_bgr, f))
    print(combined.shape, mask.shape)
    cv2.imshow('frameds', combined)
    out.write(combined)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
out.release()