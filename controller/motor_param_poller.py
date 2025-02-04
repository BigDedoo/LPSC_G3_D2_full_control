from PyQt5.QtCore import QObject, pyqtSignal
import time

class MotorParameterPoller(QObject):
    """
    Worker that polls motor parameters continuously in a separate thread.
    Polls 49 parameters for both the X and Y motors.
    """
    motorParametersUpdated = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)

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
            try:
                responses = {}
                for i in range(1, 50):  # 1 through 49
                    responses[f"X{i}"] = self.motor_model.send_command(f"XP{i:02d}R")
                    responses[f"Y{i}"] = self.motor_model.send_command(f"YP{i:02d}R")
                self.motorParametersUpdated.emit(responses)
            except Exception as e:
                self.errorOccurred.emit(f"Error in MotorParameterPoller: {e}")
            time.sleep(self.poll_interval)

    def stop(self):
        self._running = False


class MotorParameterPollerSingle(QObject):
    """
    Worker that polls motor parameters one time (1..49) but emits each pair as soon as it’s available.
    """
    motorParametersUpdated = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)

    def __init__(self, motor_model):
        super().__init__()
        self.motor_model = motor_model

    def run(self):
        all_responses = {}
        try:
            for i in range(1, 50):
                x_resp = self.motor_model.send_command(f"XP{i:02d}R")
                y_resp = self.motor_model.send_command(f"YP{i:02d}R")
                all_responses[f"X{i}"] = x_resp
                all_responses[f"Y{i}"] = y_resp
                # Emit partial update.
                self.motorParametersUpdated.emit({
                    f"X{i}": x_resp,
                    f"Y{i}": y_resp
                })
        except Exception as e:
            self.errorOccurred.emit(f"Error in MotorParameterPollerSingle: {e}")
        # Optionally, you can emit the complete dictionary.
        # self.motorParametersUpdated.emit(all_responses)
