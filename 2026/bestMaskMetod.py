import cv2, math
import numpy as np
from hard_control.abstractions import *
def normalize(img):
    return cv2.normalize(img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
def compactness(c):
    area = cv2.contourArea(c)
    perimeter = cv2.arcLength(c, True)
    if perimeter == 0:
        return 0
    # 1) Компактность (необязательно, закомментировано)
    compactness = (4 * math.pi * area) / (perimeter * perimeter)
    return compactness
def approx(cnt, k=0.02):
    perimeter = cv2.arcLength(cnt, True)
    epsilon = perimeter * k
    approx_cnt = cv2.approxPolyDP(cnt, epsilon, True)
    return approx_cnt
def HSV2Gray(img, Hk, Sk, Vk):
    h = img[:, :, 0].astype(np.float32)
    s = img[:, :, 1].astype(np.float32)
    v = img[:, :, 2].astype(np.float32)
    gray_float = (h * Hk) / 3 + (s * Sk) / 3 + (v * Vk) / 3
    gray = np.clip(gray_float, 0, 255).astype(np.uint8)
    return gray
def getCenter(contour):
    m = cv2.moments(contour)
    if m['m00'] > 0:
        color_cntr = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
        return color_cntr
    return None
