import threading
from PyQt5.QtCore import pyqtSignal, QObject
import serial
import time
import csv
import queue

class AcqModel(QObject):
    received_data_signal = pyqtSignal(str)

    def __init__(self, com_port, baud_rate, timeout):
        super().__init__()
        self.ser = serial.Serial(com_port, baud_rate, timeout=timeout)
        self.lock = threading.Lock()  # A lock to synchronize access to the serial port

    def read_serial_data(self):
        while True:
            time.sleep(0.1)
            with self.lock:  # Acquire lock before accessing the serial port
                data = self.ser.readline().decode().strip()
            if data:
                return data
            # Add any additional processing here

    def send_serial_data(self, command):
        with self.lock:  # Acquire lock before accessing the serial port
            # Convert the command to hexadecimal and append carriage return
            hex_command = ''.join(format(ord(char), '02X') for char in command)
            full_command = f"{hex_command}0D"
            command_bytes = bytes.fromhex(''.join(full_command.split()))
            self.ser.write(command_bytes)
