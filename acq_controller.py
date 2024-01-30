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
        self.sequence_thread = None  # Thread for the special sequence

        self.latest_data = None  # Shared variable for the latest received data
        self.data_lock = threading.Lock()  # Lock for thread safety

        self.acq_received_data_signal.connect(self.on_data_received)
        self.collecting_data = False
        self.collected_data = []

    def on_data_received(self, data):
        # Method to handle data received and update the shared variable
        with self.data_lock:
            self.latest_data = data
            if self.collecting_data and data != 'F':
                self.collected_data.append(data)

    def start_acq_collect_sequence(self):
        if not self.sequence_thread or not self.sequence_thread.is_alive():
            self.sequence_thread = threading.Thread(target=self.acq_collect_sequence, daemon=True)
            self.sequence_thread.start()

    def acq_collect_sequence(self):

        while True:
            if not self.collecting_data:
                self.serial_comm.send_serial_data('A')
                time.sleep(1)  # Wait for one second

            with self.data_lock:
                response = self.latest_data

            if response == 'F' and not self.collecting_data:
                self.collecting_data = True
                self.serial_comm.send_serial_data('D')  # Send 'D' after receiving 'F'

            elif response == '00000000,00000000' and self.collecting_data:
                # Stop collecting and break the loop
                self.collecting_data = False
                break
        with open('collected_data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            for data in self.collected_data:
                data_list = data.split(',')
                writer.writerow(data_list)

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
