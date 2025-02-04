from PyQt5.QtCore import QObject, QThread, pyqtSignal
import logging
from controller.acq_sequence_worker import AcqSequenceWorker
from controller.motor_param_poller import MotorParameterPollerSingle
from model.motor_model import MotorModel
from model.acq_model import AcqModel
from config import MOTOR_COM_PORT, ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT

logger = logging.getLogger(__name__)

class MainController(QObject):
    # Signals for communicating with the UI.
    acqDataReceived = pyqtSignal(str)
    motorResponseReceived = pyqtSignal(str)
    acqSequenceFinished = pyqtSignal()
    motorParametersUpdated = pyqtSignal(dict)  # This signal updates motor parameters in the view.

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

        # If you have an AcqReadWorker for continuous data reading, set it up here.
        # (Not shown in this snippet to focus on the changes.)

    def sendMotorCommand(self, command: str):
        """Send a command to the motor and emit the response."""
        response = self.motor_model.send_command(command)
        self.motorResponseReceived.emit(response)

    def sendAcqCommand(self, command: str):
        """Send a command to the acquisition card."""
        self.acq_model.send_serial_data(command)

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
        self.acq_seq_worker.finished.connect(self.acq_seq_thread.quit)
        self.acq_seq_worker.finished.connect(self.acq_seq_worker.deleteLater)
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
        Start the motor parameter poller in its own thread to retrieve motor parameters
        once (or you can modify the poller to run continuously if desired).
        """
        self.motor_poll_thread = QThread()
        self.motor_poller = MotorParameterPollerSingle(self.motor_model)
        self.motor_poller.moveToThread(self.motor_poll_thread)
        self.motor_poll_thread.started.connect(self.motor_poller.run)
        # When parameters are updated, forward the dictionary to the UI.
        self.motor_poller.motorParametersUpdated.connect(self.motorParametersUpdated.emit)
        # Quit the thread after polling is complete.
        self.motor_poller.motorParametersUpdated.connect(self.motor_poll_thread.quit)
        self.motor_poll_thread.start()

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
        self.motor_model.close()
        self.acq_model.close()
