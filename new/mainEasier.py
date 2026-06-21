import colors, traceback
from robot.findMask import *
from robot.robot import AquaRobot
try:
    aquaRobot = AquaRobot()
    aquaRobot.start(cv2=cv2)
    Yellow = colors.Yellow
    Green = colors.Green
    Red = colors.Red
    Orange = colors.Orange
    del_index_color = []
    queue = [Yellow, Green, Red]
    all_color = [Yellow, Green, Red]
    queue_name = ['Yellow', 'Green', 'Red']
    queue_color_base = [(55, 255, 255), (110, 255, 255), (0, 255, 255)]
    PID_yaw_port = PID_regulator(-0.04, 0, 0, 0)
    PID_speed_port = PID_regulator(0.0004, 0, 0, 90000)

    PID_yaw_gate = PID_regulator(-0.08, 0, 0, 0)
    PID_speed_gate = PID_regulator(0.0004, 0, 0, 90000)
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100),
                                       cv2.aruco.DetectorParameters())
#Просто проезд вперед
    aquaRobot.motor_left.set_motor(50)
    aquaRobot.motor_right.set_motor(50)
    aquaRobot.sleepV(5)
    # выполнение всех портов
    while True:
        # Переменные для хранения лучшего (самого большого) контура
        best_area = 0
        best_index = -1
        best_contours = None
        best_raw = None
        img = aquaRobot.camera.get_frame()
        output = img.copy()
        # Проходим по всем цветам в очереди
        for i, col in enumerate(queue):
            if not i in del_index_color:
                mask = FindMask(img.copy())
                # mask.normalize()
                mask.inRangeF(col)
                mask.findContours()
                cv2.drawContours(output, mask.contours, -1, queue_color_base[i], -1)
                mask.sortedContours()
                contours = mask.contours
                if contours:
                    area = cv2.contourArea(contours[0])
                    if area > best_area:
                        best_area = area
                        best_index = i
                        best_contours = contours

        if best_index != -1:

            color_max = queue[best_index]
            contours_color_max = best_contours
            c_area = best_area
            print(queue_name[best_index])
            # if 0:
            #     for i, col in enumerate(queue):
            #         if best_index != i:
            #             contours, raw = getContoursColor(col, func_get_img)
            #             if contours:
            #                 area = cv2.contourArea(contours[0])
            #                 if area > 500:
            #                     color_cntr = getCenter(contours[0])
            #                     if color_cntr is not None:
            #                         assign = best_color_cntr - color_cntr
            #                         print(assign, queue_name[i])
            #                         if abs(assign.x) < 30:
            #                             c_area = 0
            # Выбранный цвет и его контуры

            # print('c_area', c_area)
            # print(queue_name[best_index])
            # raw = best_raw # можно использовать для отладки или записи видео
            # Если площадь достаточно велика, начинаем управление
        else:
            c_area = 0
        if c_area > 300:

            # Берём первый (самый большой) контур
            largest_contour = contours_color_max[0]
            min_y_point_contour = max(largest_contour, key=lambda point: point[0].tolist()[1])[0].tolist()[1]
            # print(min_y_point_contour)
            color_cntr = FindMask(contours=[largest_contour]).getCenter()[0]
            # cv2.line(best_raw, (0, min_y_point_contour), (820, min_y_point_contour), (0, 0, 0), 3)
            # best_raw = cv2.putText(best_raw, str(min_y_point_contour), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
            #                        (255, 0, 0), 2)
            # aquaRobot.video.write(cv2.drawContours(cv2.cvtColor(best_raw, cv2.COLOR_BGR2RGB), contours_color_max, -1, (255, 0, 0), -1))
            # aquaRobot.gui.imshow('img', cv2.drawContours(cv2.cvtColor(best_raw, cv2.COLOR_BGR2RGB), contours_color_max, -1, (255, 0, 0), -1))
            # print(cntr.y * 2 - 5)
            if min_y_point_contour <= mask.cntr_frame.y * 2 - 20:
                delta_x = (mask.cntr_frame - color_cntr).x
                u = PID_yaw_port(delta_x)
                u_speed = PID_speed_port(c_area)
                aquaRobot.motor_left.set_motor(u_speed - u)
                aquaRobot.motor_right.set_motor(u_speed + u)
                print(u_speed - u, 'motor')
                print(u_speed + u, 'motor')
                # out.release()
                # exit(0)
            else:
                aquaRobot.sleepV(3)
                # Достигли нужной близости к цели – удаляем цвет из очереди и выходим
                del_index_color.append(best_index)
                # queue.pop(best_index)
                aquaRobot.motor_left.set_motor(-60 + u * 3)
                aquaRobot.motor_right.set_motor(-60 - u * 3)
                print(PID_speed_port.integral_err)
                print(PID_yaw_port.integral_err)
                if len(del_index_color) == 3:
                    aquaRobot.sleepV(1)
                else:
                    aquaRobot.sleepV(3)
                aquaRobot.motor_left.set_motor(0)
                aquaRobot.motor_right.set_motor(0)
                if len(del_index_color) == 3:
                    break
        else:

            # Если площадь мала (менее 500) – тоже вращаемся
            aquaRobot.video.write(output)
            aquaRobot.gui.imshow('img', output)
            speed = 25
            reverse = -1 if PID_yaw_port.integral_err <= 0 else 1
            aquaRobot.motor_left.set_motor(speed * ((2 * int(reverse)) - 1))
            aquaRobot.motor_right.set_motor(speed * ((-2 * int(reverse)) + 1))
    # поворот к воротам
    while True:
        img = aquaRobot.camera.get_frame()
        mask = FindMask(img)
        # mask.normalize()
        mask.inRangeF(Orange)
        mask.findContours()
        mask.sortedContours()
        contours = mask.contours
        aquaRobot.video.write(
            cv2.drawContours(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), contours[:1 + 1], -1, (255, 0, 0), -1))
        if len(contours) >= 1 + 1 and cv2.contourArea(contours[0 + 1]) > 500:
            aquaRobot.motor_left.set_motor(0)
            aquaRobot.motor_right.set_motor(0)
            break
        aquaRobot.motor_left.set_motor(30 * ((2 * int(False)) - 1))
        aquaRobot.motor_right.set_motor(30 * ((-2 * int(False)) + 1))
    # проезд через ворота
    while True:
        img = aquaRobot.camera.get_frame()
        mask = FindMask(img)
        # mask.normalize()
        mask.inRangeF(Orange)
        mask.findContours()
        mask.sortedContours()
        c = mask.contours
        masked = cv2.drawContours(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), c[:2], -1, (255, 0, 0), -1)
        print(len(c))
        if len(c) >= 2 and cv2.contourArea(c[1]) > 500:
            print(cv2.contourArea(c[1]))
            orange_cntr = FindMask(contours=[c[0]]).getCenter()[0]
            orange_cntr_2 = FindMask(contours=[c[1]]).getCenter()[0]
            cv2.circle(masked, orange_cntr.to_int(), 5, (0, 255, 0), 2)
            cv2.circle(masked, orange_cntr_2.to_int(), 5, (0, 0, 255), 2)
            cv2.circle(masked, ((orange_cntr + orange_cntr_2) / 2).to_int(), 5, (0, 255, 255), 2)
            aquaRobot.video.write(masked)
            delta_x_yaw = (mask.cntr_frame - ((orange_cntr + orange_cntr_2) / 2)).x
            delta_x_speed = abs((orange_cntr - orange_cntr_2).x)
            u = PID_yaw_gate(delta_x_yaw * 2)
            u_speed = PID_speed_gate(delta_x_speed)
            print(u, u_speed)
            aquaRobot.motor_left.set_motor(u_speed - u)
            aquaRobot.motor_right.set_motor(u_speed + u)
        else:
            aquaRobot.sleepV(2)
            aquaRobot.motor_left.set_motor(0)
            aquaRobot.motor_right.set_motor(0)
            break


except:
    print("Произошла ошибка:")
    traceback.print_exc()
