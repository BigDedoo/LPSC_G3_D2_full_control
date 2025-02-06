# controller/main_controller.py

from PyQt5.QtCore import QObject, QThread, QThreadPool, pyqtSignal
import logging
from controller.acq_sequence_worker import AcqSequenceWorker
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

        # Acquisition sequence worker & thread.
        self.acq_seq_thread = QThread()
        self.acq_seq_worker = AcqSequenceWorker(self.motor_model, self.acq_model)
        self.acq_seq_worker.moveToThread(self.acq_seq_thread)
        self.acq_seq_thread.started.connect(self.acq_seq_worker.start)
        self.acq_seq_worker.finished.connect(self.acqSequenceFinished.emit)
        self.acq_seq_worker.errorOccurred.connect(self.errorOccurred.emit)
        self.acq_seq_worker.finished.connect(self.acq_seq_thread.quit)
        self.acq_seq_worker.finished.connect(self.acq_seq_worker.deleteLater)
        self.acq_seq_thread.finished.connect(self.acq_seq_thread.deleteLater)

        # Use QThreadPool for one-shot tasks.
        self.thread_pool = QThreadPool.globalInstance()

    def sendMotorCommand(self, command: str):
        """Send a command to the motor and emit the response."""
        try:
            response = self.motor_model.send_command(command)
            self.motorResponseReceived.emit(response)
        except Exception as e:
            self.errorOccurred.emit(f"Error sending motor command: {e}")

    def sendAcqCommand(self, command: str):
        """Send a command to the acquisition card."""
        try:
            self.acq_model.send_serial_data(command)
        except Exception as e:
            self.errorOccurred.emit(f"Error sending acq command: {e}")

    def startAcqSequence(self):
        """
        Start a new acquisition sequence using the state-machine worker.
        If already running, do nothing.
        """
        if self.acq_seq_thread.isRunning():
            return
        self.acq_seq_thread.start()

    def stopAcqSequence(self):
        """Request a graceful stop of the acquisition sequence."""
        if self.acq_seq_worker:
            self.acq_seq_worker.stop()
        if self.acq_seq_thread.isRunning():
            self.acq_seq_thread.quit()
            self.acq_seq_thread.wait()

    def runMotorParameterPoller(self):
        """
        Start the one-shot motor parameter poller using QThreadPool.
        """
        from controller.motor_param_poller_runnable import MotorParameterPollerRunnable
        runnable = MotorParameterPollerRunnable(
            self.motor_model,
            update_callback=self.motorParametersUpdated.emit,
            error_callback=self.errorOccurred.emit
        )
        self.thread_pool.start(runnable)

    def startProgramUpload(self, file_path: str, program_name: str):
        """
        Launch the program uploader as a one-shot task using QThreadPool.
        """
        from controller.program_uploader_runnable import ProgramUploaderRunnable
        runnable = ProgramUploaderRunnable(
            self.motor_model,
            file_path,
            program_name,
            progress_callback=lambda msg: print(f"[Uploader] {msg}"),
            error_callback=self.errorOccurred.emit,
            finished_callback=lambda: print("Program upload finished.")
        )
        self.thread_pool.start(runnable)

    def cleanup(self):
        """Clean up and stop all threads and close serial ports."""
        if self.acq_seq_worker:
            self.acq_seq_worker.stop()
        if self.acq_seq_thread.isRunning():
            self.acq_seq_thread.quit()
            self.acq_seq_thread.wait()
        self.motor_model.close()
        self.acq_model.close()
