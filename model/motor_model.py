# model/motor_model.py

from PyQt5.QtCore import QObject
import logging
import time
from model.serial_handler import SerialHandler
from utils.protocol_formatter import ProtocolFormatter

logger = logging.getLogger(__name__)

class MotorModel(QObject):
    """
    Domain logic for the motor:
      - Formats motor commands using protocol markers.
      - Sends commands via the serial handler.
    """
    def __init__(self, port, baud_rate, timeout):
        super().__init__()
        self.serial_handler = SerialHandler(port, baud_rate, timeout)
        self.serial_handler.open()

    def send_command(self, text_command: str) -> str:
        if not self.serial_handler.ser or not self.serial_handler.ser.is_open:
            return "<NAK>Serial port not open<ETX>"
        try:
            # Use the ProtocolFormatter to build the command bytes.
            command_bytes = ProtocolFormatter.format_motor_command(text_command)
            print(f"Sending command: {text_command}")
            print(f"Command bytes: {command_bytes}")
            self.serial_handler.write_bytes(command_bytes)
            # Read the response.
            response = self.serial_handler.read_line()
            response_repr = ProtocolFormatter.parse_motor_response(response)
            print(f"Response: {response_repr}")
            return response_repr
        except Exception as e:
            print(f"Exception in send_command({text_command}): {e}")
            return f"<NAK>Error: {e}<ETX>"

    def send_raw(self, command_bytes: bytes, expected_response_length: int = None, timeout=5) -> bytes:
        self.serial_handler.write_bytes(command_bytes)
        print(command_bytes)
        if expected_response_length is None:
            return self.serial_handler.read_line().encode()
        ser = self.serial_handler.ser
        start = time.time()
        received = b""
        while len(received) < expected_response_length and (time.time() - start) < timeout:
            if ser.in_waiting:
                received += ser.read(ser.in_waiting)
            time.sleep(0.1)
        return received

    def close(self):
        self.serial_handler.close()
