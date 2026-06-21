import colors, traceback
from robot.findMask import *
from robot.giroRobot import AquaRobot
try:
    aquaRobot = AquaRobot()
    aquaRobot.start(cv2=cv2)
    # ========= Статика =========#
    Yellow = colors.Yellow
    Green = colors.Green
    Red = colors.Red
    Orange = colors.Orange
    del_index_color = []
    queue = [Yellow, Green, Red]
    all_color = [Yellow, Green, Red]
    queue_name = ['Yellow', 'Green', 'Red']
    queue_color_base = [(55, 255, 255), (110, 255, 255), (0, 255, 255)]
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100),
                                       cv2.aruco.DetectorParameters())
    #========= Конфиг =========#
    PD_speed = PID_regulator(1, 0, 0, 0)
    PD_yaw = PID_regulator(1, 0, 0, 0)
    base_speed = 30
    thresholdFindPort = 500
    thresholdVisitPort = 20
    # ========= Функции =========#
    def setYawMotor(setYaw, threshold, sleep=(1000/30)):
        nowYaw = threshold+1
        while abs(nowYaw) >= threshold:
            nowYaw = aquaRobot.giro.getYaw()-setYaw
            u = PD_yaw(nowYaw, 0)
            aquaRobot.motor_left.set_motor(u*base_speed)
            aquaRobot.motor_right.set_motor(u*base_speed)
            aquaRobot.sleepV(sleep/1000)
        return nowYaw
    #========= Проезд через ворота =========#
    aquaRobot.motor_left.set_motor(50)
    aquaRobot.motor_right.set_motor(50)
    aquaRobot.sleepV(5)
    setYawMotor(0, 10)
    # ========= Посещение портов =========#
    while True:
        img = aquaRobot.camera.get_frame()
        output = img.copy()
        best_area = thresholdFindPort
        best_index = -1
        for i, col in enumerate(queue):
            if not i in del_index_color:
                mask = FindMask(img.copy())
                mask.inRangeF(queue[i])
                mask.findContours()
                cv2.drawContours(output, mask.contours, -1, queue_color_base[i], -1)
                mask.sortedContours()
                if mask.contours:
                    area = cv2.contourArea(mask.contours[0])
                    if area > best_area:
                        best_area = area
                        best_index = i
                        best_contours = mask.contours[0]
        if best_index == -1:
            print("Not Found Port")
        else:
            print("Found Port:", queue_name[best_index], area)
            min_y_point_contour = max(best_contours, key=lambda point: point[0].tolist()[1])[0].tolist()[1]
            color_cntr = FindMask(contours=[best_contours]).getCenter()[0]
            cv2.line(output, (0, min_y_point_contour), (mask.cntr_frame.x*2, min_y_point_contour), (0, 0, 0), 3)
            output = cv2.putText(output, str(min_y_point_contour), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                   (255, 0, 0), 2)
            if min_y_point_contour <= mask.cntr_frame.y * 2 - thresholdVisitPort:
                delta_x = (mask.cntr_frame - color_cntr).x
                u = PID_yaw_port(delta_x)
                u_speed = PID_speed_port(c_area)
                aquaRobot.motor_left.set_motor(u_speed - u)
                aquaRobot.motor_right.set_motor(u_speed + u)
            else:
                aquaRobot.sleepV(3)
                del_index_color.append(best_index)


        aquaRobot.gui.imshow("Output", output)
        aquaRobot.video.write(output)



except:
    print("Произошла ошибка:")
    traceback.print_exc()
    try:
        aquaRobot.stop()
    except:
        traceback.print_exc()
