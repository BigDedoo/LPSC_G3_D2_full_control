# controller/acq_data_poller.py

import csv
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from utils.serial_mutex import acq_mutex

class AcqDataPoller(QObject):
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, acq_model, parent=None):
        super().__init__(parent)
        self.acq_model = acq_model
        self._running = True
        self.collected_data = []
        self.polling_attempts = 0
        self.max_poll_attempts = 500  # Same as used in the config for approx 10 sec
        self._mutex_locked = False

    def run(self):
        # Lock the acquisition mutex
        acq_mutex.lock()
        self._mutex_locked = True

        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        # Start polling for the "F" response
        self.pollForResponse()

    def pollForResponse(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            # Send the polling command "A"
            self.acq_model.send_serial_data("A")
            response = self.acq_model.read_serial_data()
            print(f"[AcqDataPoller] Polling: received '{response}'")
            if response == "F":
                # Once "F" is received, send "D" and begin data collection
                self.acq_model.send_serial_data("D")
                self.collected_data = []
                QTimer.singleShot(100, self.collectData)
            else:
                self.polling_attempts += 1
                if self.polling_attempts > self.max_poll_attempts:
                    self.errorOccurred.emit("Timeout polling for 'F' response in AcqDataPoller.")
                    self.stop()
                    self._release_mutex_if_needed()
                    self.finished.emit()
                    return
                QTimer.singleShot(100, self.pollForResponse)
        except Exception as e:
            self.errorOccurred.emit(f"Error in pollForResponse: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def collectData(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            data_line = self.acq_model.read_serial_data()
            print(f"[AcqDataPoller] Data line: {data_line}")
            if data_line == "00000000,00000000":
                self.saveData()
            else:
                self.collected_data.append(data_line)
                QTimer.singleShot(100, self.collectData)
        except Exception as e:
            self.errorOccurred.emit(f"Error in collectData: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def saveData(self):
        try:
            with open("requested_data.csv", 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for item in self.collected_data:
                    # Each item is assumed to be a string like "data1,data2" – we save only the first channel.
                    first_channel = item.split(',')[0]
                    writer.writerow([first_channel])
            print("[AcqDataPoller] Data saved to requested_data.csv")
        except Exception as e:
            self.errorOccurred.emit(f"Error saving data: {e}")
        self._release_mutex_if_needed()
        self.finished.emit()

    def stop(self):
        self._running = False
        self._release_mutex_if_needed()

    def _release_mutex_if_needed(self):
        if self._mutex_locked:
            acq_mutex.unlock()
            self._mutex_locked = False
