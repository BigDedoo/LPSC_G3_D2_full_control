# controller/acq_data_poller.py

import csv
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from config import MAX_POLL_ATTEMPTS
from utils.serial_mutex import acq_mutex

class AcqDataPoller(QObject):
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, acq_model, parent=None):
        super().__init__(parent)
        self.acq_model = acq_model
        self._running = True
        self.collected_data = []  # Will store 128 rows (each row is a list of 16 words)
        self.polling_attempts = 0
        self.max_poll_attempts = MAX_POLL_ATTEMPTS  # Use the same constant as before
        self._mutex_locked = False

    def run(self):
        # Lock the acquisition mutex.
        acq_mutex.lock()
        self._mutex_locked = True

        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        # Start polling for the "F" response by sending the "A" command.
        self.polling_attempts = 0
        QTimer.singleShot(100, self.pollForResponse)

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
                # Once F is received, send the DUMP command.
                self.acq_model.send_serial_data("D")
                # Begin collecting the dump data (expecting 128 lines).
                QTimer.singleShot(100, lambda: self.collectDumpData(0))
            else:
                self.polling_attempts += 1
                if self.polling_attempts > self.max_poll_attempts:
                    self.errorOccurred.emit("Timeout polling for 'F' response in AcqDataPoller.")
                    self.stop()
                    self._release_mutex_if_needed()
                    self.finished.emit()
                    return
                # Retry after a short delay.
                QTimer.singleShot(100, self.pollForResponse)
        except Exception as e:
            self.errorOccurred.emit(f"Error in pollForResponse: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def collectDumpData(self, line_count):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            # Read one line of dump data.
            line = self.acq_model.read_serial_data()
            print(f"[AcqDataPoller] Dump line {line_count+1}: {line}")
            # Check for an error response.
            if line.strip().startswith("ERR"):
                self.errorOccurred.emit(f"DUMP command error response: {line.strip()}")
                self._release_mutex_if_needed()
                self.finished.emit()
                return

            # Split the line by commas (each line must contain 16 words).
            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 16:
                self.errorOccurred.emit(f"Unexpected number of words in dump line {line_count+1}: {line}")
                self._release_mutex_if_needed()
                self.finished.emit()
                return

            self.collected_data.append(parts)

            # If we haven't collected 128 lines yet, schedule the next read.
            if line_count + 1 < 128:
                QTimer.singleShot(10, lambda: self.collectDumpData(line_count + 1))
            else:
                # All dump data collected; now save to CSV.
                self.saveData()
        except Exception as e:
            self.errorOccurred.emit(f"Error in collectDumpData: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def saveData(self):
        try:
            with open("requested_data.csv", 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                # Flatten the collected_data (a list of 128 rows of 16 words) and write each word on a new line.
                for row in self.collected_data:
                    for word in row:
                        writer.writerow([word])
            print("[AcqDataPoller] Dump data saved to requested_data.csv")
        except Exception as e:
            self.errorOccurred.emit(f"Error saving dump data: {e}")
        self._release_mutex_if_needed()
        self.finished.emit()

    def stop(self):
        self._running = False
        self._release_mutex_if_needed()

    def _release_mutex_if_needed(self):
        if self._mutex_locked:
            acq_mutex.unlock()
            self._mutex_locked = False
