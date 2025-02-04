import csv
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import time


class AcqSequenceWorker(QObject):
    """
    Revised Acquisition Sequence Worker using a state‐machine style with QTimer.
    This worker sends the initial motor commands, then for each motor profile:
      1. Sends "A" to the acq card.
      2. Sends the motor’s drive command.
      3. Polls for an "F" response (with a maximum number of attempts to avoid hangs).
      4. When "F" is received, sends "D" to the acq card.
      5. Collects data until the termination string is received.
      6. Saves the collected data to a CSV file.

    Each step is scheduled using QTimer.singleShot so that no blocking sleeps occur.
    """
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, motor_model, acq_model, parent=None):
        super().__init__(parent)
        self.motor_model = motor_model
        self.acq_model = acq_model
        self._running = True

        # Define motor profiles.
        self.motor_profiles = [
            {"label": "X", "initial": "X0+", "drive": "X-400", "csv": "acquired_data_X.csv"},
            {"label": "Y", "initial": "Y0+", "drive": "Y-400", "csv": "acquired_data_Y.csv"}
        ]
        self.current_profile_index = 0
        self.current_profile = None
        self.collected_data = []

        # For polling “F” responses.
        self.polling_attempts = 0
        self.max_poll_attempts = 100  # e.g. 100 attempts * 100ms = ~10 seconds timeout

    def run(self):
        """
        Start the sequence by sending the initial commands.
        """
        if not self._running:
            self.finished.emit()
            return

        try:
            # Send initial command for motor X.
            print("[AcqSequenceWorker] Sending initial command for motor X.")
            self.motor_model.send_command(self.motor_profiles[0]['initial'])
            QTimer.singleShot(3000, self.sendSecondMotorInitial)
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self.finished.emit()

    def sendSecondMotorInitial(self):
        """
        Send the initial command for motor Y after a delay.
        """
        if not self._running:
            self.finished.emit()
            return
        try:
            print("[AcqSequenceWorker] Sending initial command for motor Y.")
            self.motor_model.send_command(self.motor_profiles[1]['initial'])
            QTimer.singleShot(5000, self.startMotorSequence)
        except Exception as e:
            self.errorOccurred.emit(str(e))
            self.finished.emit()

    def startMotorSequence(self):
        """
        Begin processing the motor profiles.
        """
        if not self._running:
            self.finished.emit()
            return
        self.current_profile_index = 0
        self.startMotorProfile()

    def startMotorProfile(self):
        """
        Begin the sequence for the current motor profile.
        """
        if not self._running:
            self.finished.emit()
            return

        # Restart sequence if we have processed all motor profiles.
        if self.current_profile_index >= len(self.motor_profiles):
            # If continuous operation is desired, restart; otherwise, finish.
            self.current_profile_index = 0
            QTimer.singleShot(1000, self.startMotorProfile)
            return

        self.current_profile = self.motor_profiles[self.current_profile_index]
        print(f"[AcqSequenceWorker] Starting sequence for {self.current_profile['label']} motor.")

        # Step 2: Send "A" command to the acquisition card.
        self.acq_model.send_serial_data("A")

        # Step 3: Send the motor’s drive command.
        self.motor_model.send_command(self.current_profile['drive'])

        # Step 4: Start polling for the "F" response.
        self.polling_attempts = 0
        QTimer.singleShot(100, self.pollForResponse)

    def pollForResponse(self):
        """
        Poll the acquisition card by sending "A" repeatedly until "F" is received.
        Uses QTimer.singleShot to schedule each polling attempt.
        """
        if not self._running:
            self.finished.emit()
            return

        response = self.acq_model.read_serial_data()
        print(f"[AcqSequenceWorker] Polling ({self.current_profile['label']}): received '{response}'")
        if response == "F":
            # Step 5: Once "F" is received, send the "D" command.
            self.acq_model.send_serial_data("D")
            print(f"[AcqSequenceWorker] Sent 'D' command for {self.current_profile['label']} motor.")
            # Step 6: Begin collecting data.
            self.collected_data = []
            QTimer.singleShot(100, self.collectData)
        else:
            self.polling_attempts += 1
            if self.polling_attempts > self.max_poll_attempts:
                self.errorOccurred.emit(
                    f"Timeout polling for 'F' response on {self.current_profile['label']} motor."
                )
                self.stop()
                self.finished.emit()
                return
            QTimer.singleShot(100, self.pollForResponse)

    def collectData(self):
        """
        Collect data lines from the acquisition card until the termination string is received.
        """
        if not self._running:
            self.finished.emit()
            return

        data_line = self.acq_model.read_serial_data()
        print(f"[AcqSequenceWorker] Data line ({self.current_profile['label']}): {data_line}")
        if data_line == "00000000,00000000":
            # Termination string received; proceed to save data.
            self.saveData()
        else:
            self.collected_data.append(data_line)
            QTimer.singleShot(100, self.collectData)

    def saveData(self):
        """
        Save the collected data into a CSV file.
        """
        if not self._running:
            self.finished.emit()
            return

        try:
            with open(self.current_profile['csv'], 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for item in self.collected_data:
                    writer.writerow([item])
            print(f"[AcqSequenceWorker] Data saved to {self.current_profile['csv']} "
                  f"for {self.current_profile['label']} motor.")
        except Exception as e:
            self.errorOccurred.emit(str(e))
        # Step 8: Move on to the next motor profile.
        self.current_profile_index += 1
        QTimer.singleShot(1000, self.startMotorProfile)

    def stop(self):
        """
        Request a graceful shutdown of the worker.
        """
        self._running = False
        print("[AcqSequenceWorker] Stop requested.")
