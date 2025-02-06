# controller/acq_sequence_worker.py

import csv
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from utils.state_machine_builder import build_acq_state_machine
from config import MAX_POLL_ATTEMPTS

class AcqSequenceWorker(QObject):
    """
    Acquisition Sequence Worker implemented as a state machine.
    It performs the following steps for each motor profile:
      1. Sends initial motor commands (motor X then motor Y).
      2. For each motor profile:
         - Sends "A" to the acquisition card and the motor’s drive command.
         - Polls for an "F" response (with a maximum number of attempts).
         - When "F" is received, sends "D" to the acquisition card.
         - Collects data until a termination string is received.
         - Saves the data to a CSV file.
    """
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    # Signals used for state transitions.
    initDone = pyqtSignal()
    motorYDone = pyqtSignal()
    startSequenceDone = pyqtSignal()
    profileReady = pyqtSignal()
    aCommandSent = pyqtSignal()
    pollSuccess = pyqtSignal()
    pollTimeout = pyqtSignal()
    dCommandSent = pyqtSignal()
    dataCollected = pyqtSignal()
    dataSaved = pyqtSignal()

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
        self.polling_attempts = 0
        self.max_poll_attempts = MAX_POLL_ATTEMPTS

        # Use the state machine builder helper.
        self.machine = build_acq_state_machine(self)
        self.machine.finished.connect(self.finished.emit)

    def start(self):
        """Start the acquisition sequence state machine."""
        self.machine.start()

    # --- State handler methods ---
    def on_state_init(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            print("[AcqSequenceWorker] State Init: Sending initial command for motor X.")
            self.motor_model.send_command(self.motor_profiles[0]['initial'])
            QTimer.singleShot(3000, self.initDone.emit)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_init: {e}")
            self.machine.stop()

    def on_state_sendMotorY(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            print("[AcqSequenceWorker] State SendMotorY: Sending initial command for motor Y.")
            self.motor_model.send_command(self.motor_profiles[1]['initial'])
            QTimer.singleShot(5000, self.motorYDone.emit)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_sendMotorY: {e}")
            self.machine.stop()

    def on_state_startSequence(self):
        if not self._running:
            self.machine.stop()
            return
        print("[AcqSequenceWorker] State StartSequence: Initializing sequence.")
        self.current_profile_index = 0
        QTimer.singleShot(100, self.startSequenceDone.emit)

    def on_state_processProfile(self):
        if not self._running:
            self.machine.stop()
            return
        if self.current_profile_index >= len(self.motor_profiles):
            self.current_profile_index = 0  # Loop continuously.
        self.current_profile = self.motor_profiles[self.current_profile_index]
        print(f"[AcqSequenceWorker] State ProcessProfile: Processing {self.current_profile['label']} motor.")
        QTimer.singleShot(100, self.profileReady.emit)

    def on_state_sendACommand(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            print(f"[AcqSequenceWorker] State SendACommand: Sending 'A' and drive command for {self.current_profile['label']} motor.")
            self.acq_model.send_serial_data("A")
            self.motor_model.send_command(self.current_profile['drive'])
            QTimer.singleShot(100, self.aCommandSent.emit)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_sendACommand: {e}")
            self.machine.stop()

    def on_state_pollForResponse(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            response = self.acq_model.read_serial_data()
            print(f"[AcqSequenceWorker] State PollForResponse ({self.current_profile['label']}): received '{response}'")
            if response == "F":
                self.polling_attempts = 0
                self.pollSuccess.emit()
            else:
                self.polling_attempts += 1
                if self.polling_attempts > self.max_poll_attempts:
                    self.errorOccurred.emit(f"Timeout polling for 'F' on {self.current_profile['label']} motor.")
                    self.pollTimeout.emit()
                else:
                    QTimer.singleShot(100, self.on_state_pollForResponse)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_pollForResponse: {e}")
            self.machine.stop()

    def on_state_sendDCommand(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            print(f"[AcqSequenceWorker] State SendDCommand: Sending 'D' for {self.current_profile['label']} motor.")
            self.acq_model.send_serial_data("D")
            QTimer.singleShot(100, self.dCommandSent.emit)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_sendDCommand: {e}")
            self.machine.stop()

    def on_state_collectData(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            data_line = self.acq_model.read_serial_data()
            print(f"[AcqSequenceWorker] State CollectData ({self.current_profile['label']}): {data_line}")
            if data_line == "00000000,00000000":
                self.dataCollected.emit()
            else:
                self.collected_data.append(data_line)
                QTimer.singleShot(100, self.on_state_collectData)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_collectData: {e}")
            self.machine.stop()

    def on_state_saveData(self):
        if not self._running:
            self.machine.stop()
            return
        try:
            with open(self.current_profile['csv'], 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for item in self.collected_data:
                    writer.writerow([item])
            print(f"[AcqSequenceWorker] State SaveData: Data saved to {self.current_profile['csv']} for {self.current_profile['label']} motor.")
            self.current_profile_index += 1
            self.collected_data = []  # Reset for the next profile.
            QTimer.singleShot(1000, self.dataSaved.emit)
        except Exception as e:
            self.errorOccurred.emit(f"Error in state_saveData: {e}")
            self.machine.stop()

    def stop(self):
        """Request a graceful shutdown of the worker."""
        self._running = False
        print("[AcqSequenceWorker] Stop requested.")
        self.machine.stop()
