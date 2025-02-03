# model/motor_model.py

from PyQt5.QtCore import QObject
import logging
from model.serial_handler import SerialHandler
from utils.conversions import text_to_hex

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
        try:
            # Convert the command to hexadecimal.
            hex_command = text_to_hex(text_command)
            # Build the full command (using protocol markers).
            full_command = f"02 30 {hex_command} 03"
            # Remove spaces to get a continuous hex string.
            hex_string = full_command.replace(" ", "")
            # Log the commands for debugging.
            print(f"Sending command: {text_command}")
            print(f"Hex conversion: {hex_command}")
            print(f"Full command string: {full_command} -> {hex_string}")

            # Convert the hex string to bytes.
            command_bytes = bytes.fromhex(hex_string)
            print(f"Command bytes: {command_bytes}")

            # Write the bytes to the serial port.
            self.serial_handler.write_bytes(command_bytes)

            # Read the response.
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

    def close(self):
        self.serial_handler.close()
