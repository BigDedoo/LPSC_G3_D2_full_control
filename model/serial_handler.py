# model/serial_handler.py

import logging
from threading import Lock
from cpp_serial_handler import CppSerialHandler

logger = logging.getLogger(__name__)

class SerialHandler:
    """
    A serial port communication class using a C++ extension for improved performance.
    """
    def __init__(self, port, baud_rate, timeout):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.lock = Lock()
        self.cpp_handler = CppSerialHandler(port, baud_rate, timeout)
        self.is_open = False

    def open(self):
        with self.lock:
            if not self.is_open:
                try:
                    self.cpp_handler.open()
                    self.is_open = True
                    logger.info(f"Opened serial port {self.port} at {self.baud_rate} baud using C++ handler.")
                except Exception as e:
                    logger.error(f"Error opening serial port {self.port}: {e}")

    def close(self):
        with self.lock:
            if self.is_open:
                try:
                    self.cpp_handler.close()
                    self.is_open = False
                    logger.info(f"Closed serial port {self.port}.")
                except Exception as e:
                    logger.error(f"Error closing serial port {self.port}: {e}")

    def write_bytes(self, data: bytes):
        with self.lock:
            try:
                self.cpp_handler.write_bytes(data)
                logger.debug(f"Written bytes to {self.port}: {data}")
            except Exception as e:
                logger.error(f"Error writing to serial port {self.port}: {e}")

    def read_line(self) -> str:
        with self.lock:
            try:
                line_bytes = self.cpp_handler.read_line()
                line = line_bytes.decode('utf-8', errors='replace').strip()
                logger.debug(f"Read line from {self.port}: {line}")
                return line
            except Exception as e:
                logger.error(f"Error reading from serial port {self.port}: {e}")
                return ""
