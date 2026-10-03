import colors
import traceback
from robot.findMask import *
from robot.robot import AquaRobot
from control.web.webGUI import WebGUI
import RPi.GPIO as GPIO
import robot.findOpenCV as findOpenCV



def findObj(frame, paramsObj):
    try:
        lower = (int(paramsObj['h_min']), int(paramsObj['s_min']), int(paramsObj['v_min']))
        upper = (int(paramsObj['h_max']), int(paramsObj['s_max']), int(paramsObj['v_max']))
        masked = cv2.inRange(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), lower, upper)
        # Обрезка верхней части
        obrez = int(paramsObj['obrez'])
        if obrez > 0:
            masked[:obrez, :] = 0

        masked = findOpenCV.FindMask(masked)
        c = masked.findContours()
        c.compactness()


    except:
        self.frame = self.zeros_bit.copy()
        return self.frame

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN)
    print(GPIO.input(4))

    # --- Веб-интерфейс для вывода данных ---
    gui = WebGUI(host='0.0.0.0', port=5000)
    gui.start()

    aquaRobot = AquaRobot()
    aquaRobot.start(cv2=cv2)
    Red = colors.Red
    Green = colors.Green
    Yellow = colors.Yellow
    Orange = colors.Orange
    del_index_color = []
    queue = [Yellow, Green, Red]
    all_color = [Yellow, Green, Red]
    queue_name = ['Yellow', 'Green', 'Red']
    PID_yaw_port = PID_regulator(-0.04, 0, 0, 0)
    PID_speed_port = PID_regulator(0.0004, 0, 0, 90000)

    PID_yaw_gate = PID_regulator(-0.08, 0, 0, 0)
    PID_speed_gate = PID_regulator(0.0004, 0, 0, 90000)

    # выполнение всех портов
    while True:
        if not GPIO.input(4):
            print("дождалась, наконец")
            break
        else:
            print("эта поебота ждёт кнопки")
            time.sleep(0.01)

    # Просто проезд вперед
    while True:
        img = aquaRobot.camera.get_frame()
        mask = FindMask(img)
        mask.inRangeF(Orange)
        mask.findContours()
        mask.sortedContours()
        c = mask.contours
        masked = cv2.drawContours(img.copy(), c[:2], -1, (255, 0, 0), -1)
        print(len(c))
        if len(c) >= 2 and cv2.contourArea(c[1]) > 500:
            print(cv2.contourArea(c[1]))
            orange_cntr = FindMask(contours=[c[0]]).getCenter()[0]
            orange_cntr_2 = FindMask(contours=[c[1]]).getCenter()[0]
            cv2.circle(masked, orange_cntr.to_int(), 5, (0, 255, 0), 2)
            cv2.circle(masked, orange_cntr_2.to_int(), 5, (0, 0, 255), 2)
            cv2.circle(masked, ((orange_cntr + orange_cntr_2) / 2).to_int(), 5, (0, 255, 255), 2)

            # --- вывод в веб-интерфейс ---
            gui.imshow("raw", masked)
            gui.imshow("mask", mask.frame)

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
    while True:
        best_area = 0
        best_index = -1
        best_contours = None
        best_raw = None

        for i, col in enumerate(queue):
            if not i in del_index_color:
                img = aquaRobot.camera.get_frame()
                mask = FindMask(img)
                mask.inRangeF(Orange)
                mask.findContours()
                mask.sortedContours()
                contours = mask.contours
                if contours:
                    area = cv2.contourArea(contours[0])
                    if area > best_area:
                        best_area = area
                        best_index = i
                        best_contours = contours
                        best_raw = img
                        best_color_cntr = FindMask(contours=[contours[0]]).getCenter()[0]

        if best_index != -1:
            color_max = queue[best_index]
            contours_color_max = best_contours
            c_area = best_area
            print(queue_name[best_index])
        else:
            c_area = 0

        if c_area > 500:
            largest_contour = contours_color_max[0]
            min_y_point_contour = max(largest_contour, key=lambda point: point[0].tolist()[1])[0].tolist()[1]
            color_cntr = FindMask(contours=[largest_contour]).getCenter()[0]
            cv2.line(best_raw, (0, min_y_point_contour), (820, min_y_point_contour), (0, 0, 0), 3)
            best_raw = cv2.putText(best_raw, str(min_y_point_contour), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                   (255, 0, 0), 2)

            # --- вывод в веб-интерфейс ---
            best_raw = cv2.drawContours(best_raw, contours_color_max, -1, (255, 0, 0), -1)
            gui.imshow("raw", best_raw)
            gui.imshow("mask", mask.frame)

            if min_y_point_contour <= mask.cntr_frame.y * 2 - 5:
                delta_x = (mask.cntr_frame - color_cntr).x
                u = PID_yaw_port(delta_x)
                u_speed = PID_speed_port(c_area)
                aquaRobot.motor_left.set_motor(u_speed - u)
                aquaRobot.motor_right.set_motor(u_speed + u)
                print(u_speed - u, 'motor')
                print(u_speed + u, 'motor')
            else:
                aquaRobot.sleepV(2)
                del_index_color.append(best_index)
                aquaRobot.motor_left.set_motor(-35 + u * 3)
                aquaRobot.motor_right.set_motor(-35 - u * 3)
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
            speed = 25
            reverse = -1 if PID_yaw_port.integral_err <= 0 else 1
            aquaRobot.motor_left.set_motor(speed * ((2 * int(reverse)) - 1))
            aquaRobot.motor_right.set_motor(speed * ((-2 * int(reverse)) + 1))

    # поворот к воротам
    while True:
        img = aquaRobot.camera.get_frame()
        mask = FindMask(img)
        mask.inRangeF(Orange)
        mask.findContours()
        mask.sortedContours()
        contours = mask.contours

        # --- вывод в веб-интерфейс ---
        frame_vis = cv2.drawContours(img.copy(), contours[:2], -1, (255, 0, 0), -1)
        gui.imshow("raw", frame_vis)
        gui.imshow("mask", mask.frame)

        if len(contours) >= 2 and cv2.contourArea(contours[1]) > 500:
            aquaRobot.motor_left.set_motor(0)
            aquaRobot.motor_right.set_motor(0)
            break
        aquaRobot.motor_left.set_motor(30 * ((2 * int(False)) - 1))
        aquaRobot.motor_right.set_motor(30 * ((-2 * int(False)) + 1))

    # проезд через ворота
    while True:
        img = aquaRobot.camera.get_frame()
        mask = FindMask(img)
        mask.inRangeF(Orange)
        mask.findContours()
        mask.sortedContours()
        c = mask.contours
        masked = cv2.drawContours(img.copy(), c[:2], -1, (255, 0, 0), -1)
        print(len(c))
        if len(c) >= 2 and cv2.contourArea(c[1]) > 500:
            print(cv2.contourArea(c[1]))
            orange_cntr = FindMask(contours=[c[0]]).getCenter()[0]
            orange_cntr_2 = FindMask(contours=[c[1]]).getCenter()[0]
            cv2.circle(masked, orange_cntr.to_int(), 5, (0, 255, 0), 2)
            cv2.circle(masked, orange_cntr_2.to_int(), 5, (0, 0, 255), 2)
            cv2.circle(masked, ((orange_cntr + orange_cntr_2) / 2).to_int(), 5, (0, 255, 255), 2)

            # --- вывод в веб-интерфейс ---
            gui.imshow("raw", masked)
            gui.imshow("mask", mask.frame)

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

    gui.destroyAllWindows()

except:
    print("Произошла ошибка:")
    traceback.print_exc()