# model/motor_model.py

from PyQt5.QtCore import QObject, QMutexLocker
import logging
import time
from model.serial_handler import SerialHandler
from utils.conversions import text_to_hex
from utils.serial_mutex import motor_mutex  # use motor-specific mutex

logger = logging.getLogger(__name__)

class MotorModel(QObject):
    """
    Domain logic for the motor:
      - Formats motor commands with protocol markers.
      - Sends commands via the serial handler.
    """
    def __init__(self, port, baud_rate, timeout):
        super().__init__()
        self.serial_handler = SerialHandler(port, baud_rate, timeout)
        self.serial_handler.open()

    def send_command(self, text_command: str) -> str:
        if not self.serial_handler.ser or not self.serial_handler.ser.is_open:
            return "<NAK>Serial port not open<ETX>"
        # Acquire the motor-specific mutex.
        locker = QMutexLocker(motor_mutex)
        try:
            # Convert the command to hexadecimal.
            hex_command = text_to_hex(text_command)
            # Build the full command (using protocol markers).
            full_command = f"02 30 {hex_command} 03"
            hex_string = full_command.replace(" ", "")
            print(f"Sending command: {text_command}")
            print(f"Hex conversion: {hex_command}")
            print(f"Full command string: {full_command} -> {hex_string}")
            command_bytes = bytes.fromhex(hex_string)
            print(f"Command bytes: {command_bytes}")
            self.serial_handler.write_bytes(command_bytes)
            response = self.serial_handler.read_line()
            response_repr = (response
                             .replace('\x02', '<STX>')
                             .replace('\x06', '<ACK>')
                             .replace('\x03', '<ETX>')
                             .replace('\x15', '<NAK>'))
            print(f"Response: {response_repr}")
            return response_repr
        except Exception as e:
            print(f"Exception in send_command({text_command}): {e}")
            return f"<NAK>Error: {e}<ETX>"

    def send_raw(self, command_bytes: bytes, expected_response_length: int = None, timeout=5) -> bytes:
        locker = QMutexLocker(motor_mutex)
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
