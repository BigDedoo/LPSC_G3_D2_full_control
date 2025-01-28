# ----- serial_handler.py -----

import serial
import threading
import time

class SerialHandler:
    """
    A low-level serial handler that only deals with opening the port,
    reading bytes, and writing bytes. This class should be free of any
    domain-specific logic (commands, states, or protocol-level decisions).
    """

    def __init__(self, port, baud_rate, timeout):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.lock = threading.Lock()
        self.ser = None

    def open(self):
        """Open the serial port."""
        if not self.ser or not self.ser.is_open:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)

    def close(self):
        """Close the serial port if open."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def write_bytes(self, data: bytes):
        """Write raw bytes to the serial port."""
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.write(data)

    def read_line(self) -> str:
        """
        Read a line from the serial port (until newline),
        decode to string, and strip trailing whitespace.
        """
        # Sleeps or delays can also be handled at a higher level
        # if you prefer a more synchronous approach.
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return ""
            data = self.ser.readline().decode(errors='replace').strip()
        return data

    def is_open(self) -> bool:
        """Check if the serial port is open."""
        return self.ser is not None and self.ser.is_open
