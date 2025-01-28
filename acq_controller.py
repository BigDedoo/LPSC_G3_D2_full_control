# ----- acq_controller.py -----

from PyQt5.QtCore import pyqtSignal, QObject, QThread
import time
import csv

from acq_model import AcqModel
from acq_read_worker import AcqReadWorker

class AcqController(QObject):
    acq_received_data_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.serial_comm = AcqModel('COM4', 9600, 1)

        # -- Remove raw threading.Thread references --

        # QThread and Worker for reading
        self.read_thread = QThread()
        self.read_worker = AcqReadWorker(self.serial_comm)

        # Move the worker into the thread’s context
        self.read_worker.moveToThread(self.read_thread)

        # Connect signals:
        # 1) When the thread starts, call the worker’s run() method.
        self.read_thread.started.connect(self.read_worker.run)

        # 2) The worker’s dataReady -> emit our acq_received_data_signal
        self.read_worker.dataReady.connect(self.acq_received_data_signal)

        # Keep track of collecting state and data
        self.latest_data = None
        self.collecting_data = False
        self.collected_data = []

        # Connect our own signal so we can handle data
        self.acq_received_data_signal.connect(self.on_data_received)

        # For the “sequence” logic
        self.sequence_thread = None  # (still can be a raw or QThread if you prefer)

    def start_reading(self):
        """
        Start the QThread that runs the read_worker loop.
        """
        if not self.read_thread.isRunning():
            self.read_thread.start()

    def stop_reading(self):
        """
        Stop the reading thread gracefully.
        """
        if self.read_thread.isRunning():
            self.read_worker.stop()
            self.read_thread.quit()
            self.read_thread.wait()

    def on_data_received(self, data):
        # Handle data in the main (GUI) thread.
        self.latest_data = data
        if self.collecting_data and data != 'F':
            self.collected_data.append(data)

    def start_acq_collect_sequence(self):
        # This part is still a typical Python thread,
        # but you can also convert it to a QThread if you like.
        if not self.sequence_thread or not self.sequence_thread.is_alive():
            import threading
            self.sequence_thread = threading.Thread(target=self.acq_collect_sequence, daemon=True)
            self.sequence_thread.start()

    def acq_collect_sequence(self):
        # Example sequence logic
        while True:
            if not self.collecting_data:
                self.serial_comm.send_serial_data('A')
                time.sleep(1)

            response = self.latest_data

            if response == 'F' and not self.collecting_data:
                self.collecting_data = True
                self.serial_comm.send_serial_data('D')

            elif response == '00000000,00000000' and self.collecting_data:
                # Stop collecting
                self.collecting_data = False
                break

        # Save collected data
        with open('collected_data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            for data in self.collected_data:
                data_list = data.split(',')
                writer.writerow(data_list)
