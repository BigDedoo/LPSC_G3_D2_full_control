# ----- motor_controler.py -----

from PyQt5.QtCore import pyqtSignal, QObject
from motor_model import MotorModel

class MotorControler(QObject):
    ACK_SIGNAL = pyqtSignal(str)
    NAK_SIGNAL = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.motor_model = MotorModel('COM3', 9600, 1)

    def handle_user_input(self, input_data):
        """
        Process user input and interact with the motor model.
        Depending on the response, emit ACK_SIGNAL or NAK_SIGNAL.
        """
        model_answer = self.motor_model.send_command(input_data)

        if '<ACK>' in model_answer:
            self.on_ack_received(model_answer)
        elif '<NAK>' in model_answer:
            self.on_nak_received(model_answer)

    def on_ack_received(self, data):
        self.ACK_SIGNAL.emit(data)

    def on_nak_received(self, data):
        self.NAK_SIGNAL.emit(data)

    def stop_communication(self):
        self.motor_model.close_serial_port()
