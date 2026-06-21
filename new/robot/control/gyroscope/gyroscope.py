from new.robot.control.motor import motors


class Gyroscope:
    def __init__(self):
        pass
    def getYaw(self):
        return 0
    def getSpeedYaw(self):
        return 0
    def getBoostYaw(self):
        return 0
    def reboot(self):
        pass
    def stop(self):
        pass
    def __del__(self):
        self.stop()