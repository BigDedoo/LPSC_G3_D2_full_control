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
            # Convert the command to hexadecimal
            hex_command = text_to_hex(text_command)
            # For example, the protocol uses:
            #   STX (0x02), address (0x30), command, ETX (0x03)
            full_command = f"02 30 {hex_command} 03"
            command_bytes = bytes.fromhex(''.join(full_command.split()))
            self.serial_handler.write_bytes(command_bytes)
            response = self.serial_handler.read_line()
            # Replace control characters for readability
            response_repr = (response
                             .replace('\x02', '<STX>')
                             .replace('\x06', '<ACK>')
                             .replace('\x03', '<ETX>')
                             .replace('\x15', '<NAK>'))
            logger.info(f"Motor command '{text_command}' response: {response_repr}")
            return response_repr
        except Exception as e:
            logger.error(f"Error in send_command: {e}")
            return f"<NAK>Error: {e}<ETX>"

    def close(self):
        self.serial_handler.close()
