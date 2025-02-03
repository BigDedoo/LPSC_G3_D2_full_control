# controller/main_controller.py

from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal
import time
import logging

from controller.acq_sequence_worker import AcqSequenceWorker
from controller.motor_param_poller import MotorParameterPoller
from model.motor_model import MotorModel
from model.acq_model import AcqModel
from config import MOTOR_COM_PORT, ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT

logger = logging.getLogger(__name__)

class AcqReadWorker(QObject):
    """
    Worker that continuously reads acquisition data on a separate thread.
    """
    dataReady = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, acq_model):
        super().__init__()
        self.acq_model = acq_model
        self._running = True

    def run(self):
        while self._running:
            data = self.acq_model.read_serial_data()
            if data:
                self.dataReady.emit(data)
            # Sleep briefly to prevent a busy loop.
            time.sleep(0.01)
        self.finished.emit()

    def stop(self):
        self._running = False


class MainController(QObject):
    acqDataReceived = pyqtSignal(str)
    motorResponseReceived = pyqtSignal(str)
    acqSequenceFinished = pyqtSignal()
    motorParametersUpdated = pyqtSignal(dict)  # Signal to update motor parameters

    def __init__(self):
        super().__init__()
        # Initialize the motor and acquisition models.
        self.motor_model = MotorModel(MOTOR_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT)
        self.acq_model = AcqModel(ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT)

        # Set up a thread and worker for continuous acquisition data reading.
        self.acq_read_thread = QThread()
        self.acq_read_worker = AcqReadWorker(self.acq_model)
        self.acq_read_worker.moveToThread(self.acq_read_thread)
        self.acq_read_thread.started.connect(self.acq_read_worker.run)
        self.acq_read_worker.dataReady.connect(self.acqDataReceived.emit)
        self.acq_read_worker.finished.connect(self.acq_read_thread.quit)
        self.acq_read_thread.start()

        # (Remove or comment out any continuous motor parameter polling code here.)

        # Placeholders for the acquisition sequence thread/worker (if any)
        self.acq_seq_thread = None
        self.acq_seq_worker = None

    def sendMotorCommand(self, command: str):
        response = self.motor_model.send_command(command)
        self.motorResponseReceived.emit(response)

    def sendAcqCommand(self, command: str):
        self.acq_model.send_serial_data(command)

    def startAcqSequence(self):
        """
        Start a new acquisition sequence that sends the following commands in order:
          1. "A" to the acq card,
          2. "X0+" to the motor,
          3. "X-400" to the motor.
        """
        # Prevent starting if one is already running.
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
        # (Existing implementation.)
        pass

    def runMotorParameterPoller(self):
        """
        Starts the motor parameter poller worker in its own thread once.
        """
        from controller.motor_param_poller import MotorParameterPollerSingle  # import here if not at the top
        self.motor_poll_thread = QThread()
        self.motor_poller = MotorParameterPollerSingle(self.motor_model)
        self.motor_poller.moveToThread(self.motor_poll_thread)
        self.motor_poll_thread.started.connect(self.motor_poller.run)
        self.motor_poller.motorParametersUpdated.connect(self.motorParametersUpdated.emit)
        # When polling is complete, quit the thread.
        self.motor_poller.motorParametersUpdated.connect(self.motor_poll_thread.quit)
        self.motor_poll_thread.start()

    def cleanup(self):
        if self.acq_read_worker:
            self.acq_read_worker.stop()
        if self.acq_read_thread:
            self.acq_read_thread.quit()
            self.acq_read_thread.wait()
        if self.acq_seq_worker:
            self.acq_seq_worker.stop()
        if self.acq_seq_thread:
            self.acq_seq_thread.quit()
            self.acq_seq_thread.wait()
        self.motor_model.close()
        self.acq_model.close()