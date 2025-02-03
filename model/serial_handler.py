# model/serial_handler.py

import serial
import threading
import time
import logging

logger = logging.getLogger(__name__)

class SerialHandler:
    """
    A low-level serial port communication class using pyserial.
    """
    def __init__(self, port, baud_rate, timeout):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.lock = threading.Lock()
        self.ser = None

    def open(self):
        if not self.ser or not self.ser.is_open:
            try:
                self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
                logger.info(f"Opened serial port {self.port} at {self.baud_rate} baud.")
            except Exception as e:
                logger.error(f"Error opening serial port {self.port}: {e}")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info(f"Closed serial port {self.port}.")

    def write_bytes(self, data: bytes):
        with self.lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(data)
                    logger.debug(f"Written bytes to {self.port}: {data}")
                except Exception as e:
                    logger.error(f"Error writing to serial port {self.port}: {e}")
            else:
                logger.warning("Serial port is not open when trying to write.")

    def read_line(self) -> str:
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return ""
            try:
                line = self.ser.readline().decode(errors='replace').strip()
                logger.debug(f"Read line from {self.port}: {line}")
                return line
            except Exception as e:
                logger.error(f"Error reading from serial port {self.port}: {e}")
                return ""
