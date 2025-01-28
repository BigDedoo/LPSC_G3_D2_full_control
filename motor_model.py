# ----- motor_model.py -----

from PyQt5.QtCore import QObject
from serial_handler import SerialHandler

class MotorModel(QObject):
    """
    Motor-specific domain logic:
    - Prepares motor commands in the required protocol (STX, ETX, address)
    - Processes or parses the raw responses.
    - Depends on SerialHandler for the actual reading/writing of bytes.
    """

    def __init__(self, port, baud_rate, timeout):
        super().__init__()
        # Create a SerialHandler instance.
        self.serial_handler = SerialHandler(port, baud_rate, timeout)
        self.serial_handler.open()

    def send_command(self, text_command: str) -> str:
        """
        Convert the text command to the motor protocol and write it.
        Then read and parse the response to return a higher-level string.
        """
        if not self.serial_handler.is_open():
            return "<NAK>Serial port not open<ETX>"

        try:
            # Convert the text command to hexadecimal representation
            hex_command = ''.join(format(ord(char), '02X') for char in text_command)

            # Construct the full command with STX (0x02), address (0x30), ...
            full_command = f"02 30 {hex_command} 03"
            command_bytes = bytes.fromhex(''.join(full_command.split()))

            self.serial_handler.write_bytes(command_bytes)

            # Read the response (as a line of text).
            response = self.serial_handler.read_line()

            # The raw response might contain non-printable characters; let's replace them:
            response_repr = (response
                             .replace('\x02', '<STX>')
                             .replace('\x06', '<ACK>')
                             .replace('\x03', '<ETX>')
                             .replace('\x15', '<NAK>'))

            return response_repr

        except Exception as e:
            return f"<NAK>Error: {e}<ETX>"

    def close_serial_port(self):
        """Close the serial handler's port."""
        self.serial_handler.close()
