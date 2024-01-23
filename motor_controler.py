from motor_model import MotorModel
from PyQt5.QtCore import pyqtSignal, QObject


class MotorControler(QObject):
    ACK_SIGNAL = pyqtSignal(str)
    NAK_SIGNAL = pyqtSignal(str)
    def __init__(self):
        super().__init__()

        self.motor_model = MotorModel('COM3', 9600, 1)

    def handle_user_input(self, input_data):
        # Process user input and interact with the model
        model_answer = self.motor_model.send_command(input_data)
        if '<ACK>' in model_answer:
            self.on_ack_received(model_answer)
        elif '<NAK>' in model_answer:
            self.on_nak_received(model_answer)

    def on_ack_received(self, data):
        # Callback function that gets called when ACK is received
        self.ACK_SIGNAL.emit(data)

    def on_nak_received(self, data):
        # Callback function that gets called when NAK is received
        self.NAK_SIGNAL.emit(data)

    def stop_communication(self):
        # Stop or terminate communication
        if self.motor_model.ser.isOpen():
            self.motor_model.ser.close()