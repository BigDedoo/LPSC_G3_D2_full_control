# model/acq_model.py

from PyQt5.QtCore import QObject, QMutexLocker
import time
import logging
from model.serial_handler import SerialHandler
from utils.conversions import text_to_hex
from utils.serial_mutex import acq_mutex  # use acquisition-specific mutex

logger = logging.getLogger(__name__)

class AcqModel(QObject):
    """
    Domain logic for the acquisition card:
      - Reads and sends commands through the serial port.
    """
    def __init__(self, port, baud_rate, timeout):
        super().__init__()
        self.serial_handler = SerialHandler(port, baud_rate, timeout)
        self.serial_handler.open()

    def read_serial_data(self) -> str:
        start_time = time.time()
        while True:
            if time.time() - start_time > self.serial_handler.timeout:
                logger.warning("Timeout waiting for acquisition data.")
                return ""
            data = self.serial_handler.read_line()
            if data:
                logger.debug(f"Acquisition data received: {data}")
                return data
            time.sleep(0.1)

    def send_serial_data(self, command: str):
        locker = QMutexLocker(acq_mutex)
        # Updated check: use is_open instead of non-existent 'ser'
        if not self.serial_handler.is_open:
            logger.error("Acquisition serial port not open")
            return
        try:
            hex_command = text_to_hex(command)
            full_command = f"{hex_command}0D"  # Append carriage return if required.
            command_bytes = bytes.fromhex(full_command)
            self.serial_handler.write_bytes(command_bytes)
            logger.info(f"Sent acquisition command: {command}")
        except Exception as e:
            logger.error(f"Error sending acquisition command: {e}")

    def close(self):
        self.serial_handler.close()
