# controller/motor_param_poller_runnable.py

from PyQt5.QtCore import QRunnable, pyqtSlot
from controller.motor_param_poller import MotorParameterPollerSingle

class MotorParameterPollerRunnable(QRunnable):
    """
    QRunnable wrapper for the one-shot motor parameter poller.
    """
    def __init__(self, motor_model, update_callback, error_callback):
        super().__init__()
        self.poller = MotorParameterPollerSingle(motor_model)
        self.poller.motorParametersUpdated.connect(update_callback)
        self.poller.errorOccurred.connect(error_callback)

    @pyqtSlot()
    def run(self):
        self.poller.run()
