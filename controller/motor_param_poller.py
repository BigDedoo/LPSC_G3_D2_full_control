# ----- controller/motor_param_poller.py -----
from PyQt5.QtCore import QObject, pyqtSignal
import time

class MotorParameterPoller(QObject):
    """
    Worker that polls motor parameters continuously in a separate thread.
    Polls 49 parameters for both the X and Y motors.
    """
    motorParametersUpdated = pyqtSignal(dict)

    def __init__(self, motor_model, poll_interval=1000):
        """
        :param motor_model: Instance of MotorModel to use for sending commands.
        :param poll_interval: Poll interval in milliseconds.
        """
        super().__init__()
        self.motor_model = motor_model
        self.poll_interval = poll_interval / 1000.0  # convert to seconds
        self._running = True

    def run(self):
        while self._running:
            responses = {}
            for i in range(1, 50):  # 1 through 49
                responses[f"X{i}"] = self.motor_model.send_command(f"XP{i:02d}R")
                responses[f"Y{i}"] = self.motor_model.send_command(f"YP{i:02d}R")
            self.motorParametersUpdated.emit(responses)
            time.sleep(self.poll_interval)

    def stop(self):
        self._running = False


class MotorParameterPollerSingle(QObject):
    """
    Worker that polls motor parameters one time.
    Polls 49 parameters for both the X and Y motors.
    """
    motorParametersUpdated = pyqtSignal(dict)

    def __init__(self, motor_model):
        super().__init__()
        self.motor_model = motor_model

    def run(self):
        responses = {}
        for i in range(1, 50):  # 1 through 49
            responses[f"X{i}"] = self.motor_model.send_command(f"XP{i:02d}R")
            responses[f"Y{i}"] = self.motor_model.send_command(f"YP{i:02d}R")
        self.motorParametersUpdated.emit(responses)
