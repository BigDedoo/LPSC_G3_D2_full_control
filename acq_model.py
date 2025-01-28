# ----- acq_model.py -----

from PyQt5.QtCore import pyqtSignal, QObject
import time
from serial_handler import SerialHandler

class AcqModel(QObject):
    received_data_signal = pyqtSignal(str)

    def __init__(self, com_port, baud_rate, timeout):
        super().__init__()
        self.serial_handler = SerialHandler(com_port, baud_rate, timeout)
        self.serial_handler.open()

    def read_serial_data(self) -> str:
        """
        High-level method that returns the next line of data.
        Could contain domain logic about how we parse or handle it
        (e.g., if we expect certain tokens).
        """
        # Just read from the SerialHandler
        # We can add domain logic here (e.g., parse partial lines or wait).
        while True:
            time.sleep(0.1)
            data = self.serial_handler.read_line()
            if data:
                return data
        # If there's no data, eventually we might return "" or raise an exception.

    def send_serial_data(self, command: str):
        """
        Convert the domain command to the correct protocol format
        (e.g., hex, add 0D for carriage return, etc.) before sending.
        """
        if not self.serial_handler.is_open():
            return

        # Convert the command to hexadecimal and append carriage return
        hex_command = ''.join(format(ord(char), '02X') for char in command)
        full_command = f"{hex_command}0D"
        command_bytes = bytes.fromhex(''.join(full_command.split()))

        self.serial_handler.write_bytes(command_bytes)

    def close_serial_port(self):
        self.serial_handler.close()
