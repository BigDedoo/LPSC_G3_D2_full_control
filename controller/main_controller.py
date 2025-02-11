# controller/main_controller.py

from PyQt5.QtCore import QObject, QThread, pyqtSignal
import logging
from controller.acq_sequence_worker import AcqSequenceWorker
from controller.motor_param_poller import MotorParameterPollerSingle
from controller.program_uploader import ProgramUploader
from model.motor_model import MotorModel
from model.acq_model import AcqModel
from config import MOTOR_COM_PORT, ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT

logger = logging.getLogger(__name__)

class MainController(QObject):
    # Signals for communicating with the UI.
    acqDataReceived = pyqtSignal(str)
    motorResponseReceived = pyqtSignal(str)
    acqSequenceFinished = pyqtSignal()
    motorParametersUpdated = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)  # Centralized error signal.

    def __init__(self):
        super().__init__()
        # Initialize the motor and acquisition models.
        self.motor_model = MotorModel(MOTOR_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT)
        self.acq_model = AcqModel(ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT)

        # Placeholders for the acquisition sequence worker/thread.
        self.acq_seq_thread = None
        self.acq_seq_worker = None

        # Placeholders for the motor parameter poller thread/worker.
        self.motor_poll_thread = None
        self.motor_poller = None

        # Placeholders for the acquisition data poller thread/worker.
        self.acq_data_poll_thread = None
        self.acq_data_poll_worker = None

    def sendMotorCommand(self, command: str):
        """Send a command to the motor and emit the response."""
        try:
            response = self.motor_model.send_command(command)
            self.motorResponseReceived.emit(response)
        except Exception as e:
            self.errorOccurred.emit(f"Error sending motor command: {e}")

    def sendAcqCommand(self, command: str):
        """
        Send a command to the acquisition card and emit the response.
        Previously, this method only sent the command.
        Now it reads the response and emits it so that the Acq data display is updated.
        """
        try:
            self.acq_model.send_serial_data(command)
            # Read the response from the acq card
            response = self.acq_model.read_serial_data()
            self.acqDataReceived.emit(response)
        except Exception as e:
            self.errorOccurred.emit(f"Error sending acq command: {e}")

    def startAcqSequence(self):
        """
        Start a new acquisition sequence using the event-driven worker.
        Prevents starting if one is already running.
        """
        if self.acq_seq_thread and self.acq_seq_thread.isRunning():
            return

        self.acq_seq_thread = QThread()
        self.acq_seq_worker = AcqSequenceWorker(self.motor_model, self.acq_model)
        self.acq_seq_worker.moveToThread(self.acq_seq_thread)
        self.acq_seq_thread.started.connect(self.acq_seq_worker.run)
        self.acq_seq_worker.finished.connect(self.acqSequenceFinished.emit)
        self.acq_seq_worker.finished.connect(lambda: setattr(self, 'acq_seq_worker', None))
        self.acq_seq_worker.finished.connect(self.acq_seq_thread.quit)
        self.acq_seq_worker.finished.connect(self.acq_seq_worker.deleteLater)
        self.acq_seq_thread.finished.connect(lambda: setattr(self, 'acq_seq_thread', None))
        self.acq_seq_thread.finished.connect(self.acq_seq_thread.deleteLater)
        self.acq_seq_thread.start()

    def stopAcqSequence(self):
        """Request a graceful stop of the acquisition sequence."""
        if self.acq_seq_worker:
            self.acq_seq_worker.stop()
        if self.acq_seq_thread:
            self.acq_seq_thread.quit()
            self.acq_seq_thread.wait()

    def runMotorParameterPoller(self):
        """
        Start the motor parameter poller in its own thread to retrieve motor parameters.
        """
        self.motor_poll_thread = QThread()
        self.motor_poller = MotorParameterPollerSingle(self.motor_model)
        self.motor_poller.moveToThread(self.motor_poll_thread)
        self.motor_poll_thread.started.connect(self.motor_poller.run)
        self.motor_poller.motorParametersUpdated.connect(self.motorParametersUpdated.emit)
        self.motor_poller.motorParametersUpdated.connect(self.motor_poll_thread.quit)
        self.motor_poll_thread.start()

    def startProgramUpload(self, file_path: str, program_name: str):
        """
        Launch the program uploader in a separate thread.
        """
        self.prog_upload_thread = QThread()
        self.prog_uploader = ProgramUploader(self.motor_model, file_path, program_name)
        self.prog_uploader.moveToThread(self.prog_upload_thread)
        self.prog_upload_thread.started.connect(self.prog_uploader.upload)
        self.prog_uploader.progressUpdated.connect(lambda msg: print(f"[Uploader] {msg}"))
        self.prog_uploader.errorOccurred.connect(self.errorOccurred.emit)
        self.prog_uploader.finished.connect(self.prog_upload_thread.quit)
        self.prog_uploader.finished.connect(self.prog_uploader.deleteLater)
        self.prog_upload_thread.finished.connect(self.prog_upload_thread.deleteLater)
        self.prog_upload_thread.start()

    def startAcqDataPoller(self):
        """
        Start the acquisition data poller in its own thread to poll the acq card and save data.
        """
        if self.acq_data_poll_thread and self.acq_data_poll_thread.isRunning():
            return

        from controller.acq_data_poller import AcqDataPoller
        self.acq_data_poll_thread = QThread()
        self.acq_data_poll_worker = AcqDataPoller(self.acq_model)
        self.acq_data_poll_worker.moveToThread(self.acq_data_poll_thread)
        self.acq_data_poll_thread.started.connect(self.acq_data_poll_worker.run)
        self.acq_data_poll_worker.finished.connect(lambda: self.acqDataReceived.emit("Acquisition poll finished."))
        self.acq_data_poll_worker.finished.connect(self.acq_data_poll_thread.quit)
        self.acq_data_poll_worker.finished.connect(self.acq_data_poll_worker.deleteLater)
        self.acq_data_poll_thread.finished.connect(lambda: setattr(self, 'acq_data_poll_thread', None))
        self.acq_data_poll_thread.finished.connect(self.acq_data_poll_thread.deleteLater)
        self.acq_data_poll_thread.start()

    def cleanup(self):
        """Clean up and stop all threads and close serial ports."""
        if self.acq_seq_worker:
            self.acq_seq_worker.stop()
        if self.acq_seq_thread:
            self.acq_seq_thread.quit()
            self.acq_seq_thread.wait()
        if self.motor_poll_thread:
            self.motor_poll_thread.quit()
            self.motor_poll_thread.wait()
        if self.acq_data_poll_worker:
            self.acq_data_poll_worker.stop()
        if self.acq_data_poll_thread:
            self.acq_data_poll_thread.quit()
            self.acq_data_poll_thread.wait()
        self.motor_model.close()
        self.acq_model.close()
