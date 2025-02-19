# controller/alternative_acq_sequence_worker.py
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from utils.serial_mutex import acq_mutex

logger = logging.getLogger(__name__)

class AlternativeAcqSequenceWorker(QObject):
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)
    motorResponse = pyqtSignal(str)
    acqData = pyqtSignal(str)

    def __init__(self, motor_model, acq_model, parent=None):
        super().__init__(parent)
        self.motor_model = motor_model
        self.acq_model = acq_model
        self._running = True

        # Use same labels and initial commands as the regular sequence,
        # but with alternative drive commands ("X+1" / "Y+1")
        self.motor_profiles = [
            {"label": "X", "initial": "X0+", "alt_drive": "X-1", "csv": "acquired_data_X.csv"},
            {"label": "Y", "initial": "Y0+", "alt_drive": "Y-1", "csv": "acquired_data_Y.csv"}
        ]
        self.current_profile_index = 0
        self.current_profile = None

        self._mutex_locked = False

    def run(self):
        acq_mutex.lock()
        self._mutex_locked = True
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            logger.info("[AltAcqSequenceWorker] Sending initial command for motor X.")
            response = self.motor_model.send_command(self.motor_profiles[0]['initial'])
            self.motorResponse.emit(response)
            # Immediately call the next step without delay.
            self.sendSecondMotorInitial()
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
            logger.info("[AltAcqSequenceWorker] Sending initial command for motor Y.")
            response = self.motor_model.send_command(self.motor_profiles[1]['initial'])
            self.motorResponse.emit(response)
            # Immediately start the alternative sequence.
            QTimer.singleShot(2000, self.startAlternativeSequence)
        except Exception as e:
            self.errorOccurred.emit(f"Error in sendSecondMotorInitial(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def startAlternativeSequence(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return
        self.current_profile_index = 0
        self.processCurrentMotor()

    def processCurrentMotor(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        if self.current_profile_index >= len(self.motor_profiles):
            logger.info("[AltAcqSequenceWorker] Completed alternative sequence for all motors.")
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        self.current_profile = self.motor_profiles[self.current_profile_index]
        logger.info(f"[AltAcqSequenceWorker] Starting alternative sequence for {self.current_profile['label']} motor.")
        self.alternativeStep()

    def alternativeStep(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            logger.info(f"[AltAcqSequenceWorker] Sending alternative drive command {self.current_profile['alt_drive']} for {self.current_profile['label']} motor.")
            response = self.motor_model.send_command(self.current_profile['alt_drive'])
            self.motorResponse.emit(response)
            # Immediately proceed to send 'R' command.
            self.sendRtoAcq()
        except Exception as e:
            self.errorOccurred.emit(f"Error in alternativeStep(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def sendRtoAcq(self):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            logger.info(f"[AltAcqSequenceWorker] Sending 'R' command to acquisition card for {self.current_profile['label']} motor.")
            self.acq_model.send_serial_data("R")
            response = self.acq_model.read_serial_data()
            logger.info(f"[AltAcqSequenceWorker] Received response from acq card: {response}")
            self.acqData.emit(response)
            # Immediately process the acq response.
            self.alternativeStep()
        except Exception as e:
            self.errorOccurred.emit(f"Error in sendRtoAcq(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def sendSUItoMotor(self, acq_response):
        if not self._running:
            self._release_mutex_if_needed()
            self.finished.emit()
            return

        try:
            logger.info(f"[AltAcqSequenceWorker] Sending 'SUI' command to motor for {self.current_profile['label']} motor.")
            sui_response = self.motor_model.send_command("SUI")
            logger.info(f"[AltAcqSequenceWorker] Received SUI response: {sui_response}")
            self.motorResponse.emit(sui_response)
            # If the SUI response contains "00", repeat the alternative step; otherwise, finish this motor.
            if "00" in sui_response:
                logger.info(f"[AltAcqSequenceWorker] SUI response contains '00'. Repeating alternative step for {self.current_profile['label']} motor.")
                self.alternativeStep()
            else:
                logger.info(f"[AltAcqSequenceWorker] SUI response does not contain '00'. Finishing sequence for {self.current_profile['label']} motor.")
                self.current_profile_index += 1
                self.processCurrentMotor()
        except Exception as e:
            self.errorOccurred.emit(f"Error in sendSUItoMotor(): {e}")
            self._release_mutex_if_needed()
            self.finished.emit()

    def stop(self):
        self._running = False
        self._release_mutex_if_needed()

    def _release_mutex_if_needed(self):
        if self._mutex_locked:
            acq_mutex.unlock()
            self._mutex_locked = False
