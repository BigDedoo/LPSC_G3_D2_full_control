from acq_model import AcqModel
from PyQt5.QtCore import pyqtSignal, QObject
import threading
import time
import csv
import queue

class AcqController(QObject):
    acq_received_data_signal = pyqtSignal(str)
    def __init__(self):

        super().__init__()
        self.serial_comm = AcqModel('COM4', 9600, 1)
        self.read_thread = None
        self.write_thread = None

    def start_reading(self):
        if not self.read_thread or not self.read_thread.is_alive():
            self.read_thread = threading.Thread(target=self.threaded_read_serial_data, daemon=True)
            self.read_thread.start()

    def threaded_read_serial_data(self):
        # Thread's target function
        while True:
            data = self.serial_comm.read_serial_data()
            if data:
                self.acq_received_data_signal.emit(data)  # Emit signal within the thread


    def start_writing(self):
        def continuous_write():
            while True:
                self.serial_comm.send_serial_data('R')
                time.sleep(1)  # Add a delay to avoid overwhelming the serial port

        if not self.write_thread or not self.write_thread.is_alive():
            self.write_thread = threading.Thread(target=continuous_write, daemon=True)
            self.write_thread.start()