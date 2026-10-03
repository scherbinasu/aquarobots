import cv2
try:
    from cv2 import cv2
except ImportError:
    pass
from myClassMathObj import *

COLOR_SPACE_RGB = cv2.COLOR_RGB2HSV
COLOR_SPACE_BGR = cv2.COLOR_BGR2HSV
COLOR_SPACE_HSV = -1#cv2.COLOR_HSV2HSV



class FindFrame:
    __center = None
    __colorSpace = None

    def __init__(self, frame, colorSpace):
        if colorSpace == COLOR_SPACE_HSV:
            self.frame = frame
        else:
            self.frame = cv2.cvtColor(frame, colorSpace)


    def normalize(self):
        self.frame = cv2.normalize(self.frame, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        return

    def HSV2Gray(self, Hk, Sk, Vk):
        img = self.frame
        h = img[:, :, 0].astype(np.float32)
        s = img[:, :, 1].astype(np.float32)
        v = img[:, :, 2].astype(np.float32)
        gray_float = (h * Hk) / 3 + (s * Sk) / 3 + (v * Vk) / 3
        gray = np.clip(gray_float, 0, 255).astype(np.uint8)
        self.frame = gray
        return gray

    def getCenter(self):
        if self.__center is None:
            self.__center = Point(tuple(map(lambda x: x / 2, self.frame.shape[1::-1])))
        return self.__center

    def cropping(self, fromX, toX, fromY, toY):
        self.frame = self.frame[fromY:toY, fromX:toX]
        self.__center = None

    def inRangeF(self, color=None):
        """Возвращает бинарную маску для заданного цвета."""
        try:
            img = self.frame
            lower = (int(color['h_min']), int(color['s_min']), int(color['v_min']))
            upper = (int(color['h_max']), int(color['s_max']), int(color['v_max']))
            masked = cv2.inRange(cv2.cvtColor(img, self.__colorSpace), lower, upper)
            # Обрезка верхней части
            obrez = int(color['obrez'])
            if obrez > 0:
                masked[:obrez, :] = 0
            return FindMask(masked)
        except:
            self.frame = self.zeros_bit.copy()
            return FindMask(np.zeros(list(map(lambda x: x * 2, list(getCenter).__reverse__())) + [1], np.uint8))


class FindMask:
    __center = None
    __moment = None

    def __init__(self, mask):
        self.mask = mask

    def getCenter(self):
        if self.__center is None or self.__moment is None:
            __moment = cv2.moments(self.mask)
            if m['m00'] > 0:
                self.__center = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
            else:
                self.__center = 0
        return self.__center


    def findContours(self):
        return FindContours(cv2.findContours(self.mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0])


class FindContours:
    def __init__(self, Contours):
        self.contours = map(lambda x: FindContour(x), Contours)

    def compactness(self):
        return list(map(lambda x: x.compactness, self.contours))

    def approx(self, k=0.02):
        return list(map(lambda x: x.approx(k), self.contours))

    def getCenter(self):
        return list(map(lambda x: x.getCenter, self.contours))
    def Moment(self):
        return list(map(lambda x: x.getCenter, self.contours))

    def sortedContoursArea(self):
        contours = sorted(self.contours, key=lambda x: x.getArea(), reverse=True)
        self.contours = contours
        return contours

    def __iter__(self):
        return iter(self.contours)


class FindContour:
    __compactness = None
    __center = None
    __area = None
    __arcLength = None
    __Orientation = None
    __moment = None

    def __init__(self, contour):
        self.contour = contour

    def __remove_param(self):
        self.__compactness = None
        self.__center = None
        self.__area = None
        self.__arcLength = None
        self.__Orientation = None
        self.__moment = None

    # ========== Преобразования ==========#
    def approx(self, k=0.02):
        perimeter = cv2.arcLength(self.contour, True)
        epsilon = perimeter * k
        self.contour = cv2.approxPolyDP(self.contour, epsilon, True)
        self.__remove_param()

    # ========== Параметры ==========#
    def compactness(self):
        if self.__compactness is None:
            area = self.getArea()
            perimeter = cv2.arcLength(self.contour, True)
            if perimeter == 0 or area == 0:
                self.__compactness = 0
            else:
                self.__compactness = (4 * math.pi * area) / (perimeter * perimeter)
        return self.__compactness

    def getCenter(self):
        if self.__center is None:
            m = cv2.moments(self.contour)
            if m['m00'] > 0:
                self.__center = Point((m["m10"] / m["m00"], m["m01"] / m["m00"]))
            else:
                self.__center = 0
        return self.__center

    def getArea(self):
        if self.__area is None:
            self.__area = cv2.contourArea(self.contour)
        return self.__area

    def arcLength(self):
        if self.__arcLength is None:
            self.__arcLength = cv2.arcLength(self.contour, True)
        return self.__arcLength

    def getOrientation(self):
        """Возвращает угол ориентации контура (в градусах, от 0 до 180)"""
        if self.__Orientation is None:
            pts = self.contour
            sz = len(pts)
            data_pts = np.empty((sz, 2), dtype=np.float64)
            for i in range(data_pts.shape[0]):
                data_pts[i, 0] = pts[i, 0, 0]
                data_pts[i, 1] = pts[i, 0, 1]
            mean = np.empty((0))
            mean, eigenvectors, _ = cv2.PCACompute2(data_pts, mean)
            vx, vy = eigenvectors[0]
            angle_rad = math.atan2(vy, vx)
            self.__Orientation = Direction(angle_rad)
        return self.__Orientation
