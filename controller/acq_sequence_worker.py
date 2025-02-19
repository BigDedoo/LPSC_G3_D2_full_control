# controller/acq_sequence_worker.py
import csv
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import time
from config import MAX_POLL_ATTEMPTS
from utils.serial_mutex import acq_mutex  # use acquisition-specific mutex

class AcqSequenceWorker(QObject):
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)
    motorResponse = pyqtSignal(str)
    acqData = pyqtSignal(str)

    def __init__(self, motor_model, acq_model, parent=None):
        super().__init__(parent)
        self.motor_model = motor_model
        self.acq_model = acq_model
        self._running = True

        self.motor_profiles = [
            {"label": "X", "initial": "X0+", "drive": "X-400", "csv": "acquired_data_X.csv"},
            {"label": "Y", "initial": "Y0+", "drive": "Y-400", "csv": "acquired_data_Y.csv"}
        ]
        self.current_profile_index = 0
        self.current_profile = None
        self.collected_data = []  # For dump data: list of 128 rows (each row is a list of 16 words)

        self.polling_attempts = 0
        self.max_poll_attempts = MAX_POLL_ATTEMPTS

        self._mutex_locked = False

    def run(self):
        acq_mutex.lock()
        self._mutex_locked = True
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            response = self.motor_model.send_command(self.motor_profiles[0]['initial'])
            self.motorResponse.emit(response)
            print("[AcqSequenceWorker] Sending initial command for motor X.")
            QTimer.singleShot(3000, self.sendSecondMotorInitial)
        except Exception as e:
            self.errorOccurred.emit(f"Error in run(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def sendSecondMotorInitial(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return
        try:
            response = self.motor_model.send_command(self.motor_profiles[1]['initial'])
            self.motorResponse.emit(response)
            print("[AcqSequenceWorker] Sending initial command for motor Y.")
            QTimer.singleShot(5000, self.startMotorSequence)
        except Exception as e:
            self.errorOccurred.emit(f"Error in sendSecondMotorInitial(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def startMotorSequence(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return
        self.current_profile_index = 0
        self.startMotorProfile()

    def startMotorProfile(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        if self.current_profile_index >= len(self.motor_profiles):
            print("[AcqSequenceWorker] All motor profiles processed. Finishing sequence.")
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        self.current_profile = self.motor_profiles[self.current_profile_index]
        print(f"[AcqSequenceWorker] Starting sequence for {self.current_profile['label']} motor.")
        try:
            # Step 2: Send "A" command to the acquisition card.
            self.acq_model.send_serial_data("A")
            # Send the motor’s drive command and capture its response.
            motor_resp = self.motor_model.send_command(self.current_profile['drive'])
            self.motorResponse.emit(motor_resp)
            # Send the appropriate SC command.
            if self.current_profile['label'] == "X":
                self.acq_model.send_serial_data("SC,002,005")
            elif self.current_profile['label'] == "Y":
                self.acq_model.send_serial_data("SC,008,005")
            QTimer.singleShot(100, self.waitForSCResponse)
        except Exception as e:
            self.errorOccurred.emit(f"Error sending commands for motor {self.current_profile['label']}: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()
            return

    def waitForSCResponse(self):
        try:
            response = self.acq_model.read_serial_data()
            self.acqData.emit(response)
            print(f"[AcqSequenceWorker] SC response: '{response}'")
            if response and "OK" in response:
                QTimer.singleShot(100, self.pollForResponse)
            else:
                QTimer.singleShot(100, self.waitForSCResponse)
        except Exception as e:
            self.errorOccurred.emit(f"Error waiting for SC response: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def pollForResponse(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            self.acq_model.send_serial_data("A")
            response = self.acq_model.read_serial_data()
            self.acqData.emit(response)
            print(f"[AcqSequenceWorker] Polling ({self.current_profile['label']}): received '{response}'")
            if response == "F":
                self.acq_model.send_serial_data("D")
                print(f"[AcqSequenceWorker] Sent 'D' command for {self.current_profile['label']} motor.")
                self.collected_data = []  # Reset dump data collection
                QTimer.singleShot(100, lambda: self.collectDumpData(0))
            else:
                self.polling_attempts += 1
                if self.polling_attempts > self.max_poll_attempts:
                    self.errorOccurred.emit(f"Timeout polling for 'F' response on {self.current_profile['label']} motor.")
                    self.stop()
                    self._release_mutex_if_needed()
                    self.finished.emit()
                    return
                QTimer.singleShot(100, self.pollForResponse)
        except Exception as e:
            self.errorOccurred.emit(f"Error in pollForResponse(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def collectDumpData(self, line_count):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            line = self.acq_model.read_serial_data()
            self.acqData.emit(line)
            print(f"[AcqSequenceWorker] Dump line {line_count+1}: {line}")
            if line.strip().startswith("ERR"):
                self.errorOccurred.emit(f"DUMP command error response: {line.strip()}")
                self._release_mutex_if_needed()
                self.finished.emit()
                return

            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 16:
                self.errorOccurred.emit(f"Unexpected number of words in dump line {line_count+1}: {line}")
                self._release_mutex_if_needed()
                self.finished.emit()
                return

            self.collected_data.append(parts)

            if line_count + 1 < 128:
                QTimer.singleShot(10, lambda: self.collectDumpData(line_count + 1))
            else:
                self.saveData()
        except Exception as e:
            self.errorOccurred.emit(f"Error in collectDumpData: {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def saveData(self):
        try:
            with open("requested_data.csv", 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for row in self.collected_data:
                    for word in row:
                        writer.writerow([word])
            print("[AcqSequenceWorker] Dump data saved to requested_data.csv")
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
