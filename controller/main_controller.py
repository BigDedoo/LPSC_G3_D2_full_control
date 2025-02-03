# controller/main_controller.py

from PyQt5.QtCore import QObject, QThread, pyqtSignal
import time
import logging

from model.motor_model import MotorModel
from model.acq_model import AcqModel
from config import MOTOR_COM_PORT, ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT

logger = logging.getLogger(__name__)


###############################################################################
# Worker classes to run tasks in separate threads
###############################################################################

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


class AcqSequenceWorker(QObject):
    """
    Worker that performs an acquisition sequence (e.g. motor move + acquire).
    """
    finished = pyqtSignal()

    def __init__(self, motor_model, acq_model):
        super().__init__()
        self.motor_model = motor_model
        self.acq_model = acq_model
        self._running = True

    def run(self):
        # Example: perform 10 iterations of a move and acquire
        for i in range(10):
            if not self._running:
                break
            # Send a motor command (e.g. "X-1")
            motor_response = self.motor_model.send_command("X-1")
            logger.debug(f"Iteration {i + 1}: Motor response: {motor_response}")
            # Then send an acquisition command (e.g. "R")
            self.acq_model.send_serial_data("R")
            # Delay between iterations (adjust as needed)
            time.sleep(0.1)
        self.finished.emit()

    def stop(self):
        self._running = False


###############################################################################
# Main Controller
###############################################################################

class MainController(QObject):
    """
    The main controller that glues the model (domain logic) and view (UI) together.
    """
    acqDataReceived = pyqtSignal(str)
    motorResponseReceived = pyqtSignal(str)
    acqSequenceFinished = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Initialize the motor and acquisition models.
        self.motor_model = MotorModel(MOTOR_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT)
        self.acq_model = AcqModel(ACQ_COM_PORT, BAUD_RATE, SERIAL_TIMEOUT)

        # Set up a thread and worker to continuously read acquisition data.
        self.acq_read_thread = QThread()
        self.acq_read_worker = AcqReadWorker(self.acq_model)
        self.acq_read_worker.moveToThread(self.acq_read_thread)
        self.acq_read_thread.started.connect(self.acq_read_worker.run)
        self.acq_read_worker.dataReady.connect(self.acqDataReceived.emit)
        self.acq_read_worker.finished.connect(self.acq_read_thread.quit)
        self.acq_read_thread.start()

        # Placeholders for the acquisition sequence thread/worker.
        self.acq_seq_thread = None
        self.acq_seq_worker = None

    def sendMotorCommand(self, command: str):
        response = self.motor_model.send_command(command)
        self.motorResponseReceived.emit(response)

    def sendAcqCommand(self, command: str):
        self.acq_model.send_serial_data(command)

    def startAcqSequence(self):
        # Do not start a new sequence if one is already running.
        if self.acq_seq_thread and self.acq_seq_thread.isRunning():
            return
        self.acq_seq_thread = QThread()
        self.acq_seq_worker = AcqSequenceWorker(self.motor_model, self.acq_model)
        self.acq_seq_worker.moveToThread(self.acq_seq_thread)
        self.acq_seq_thread.started.connect(self.acq_seq_worker.run)
        self.acq_seq_worker.finished.connect(self.acqSequenceFinished.emit)
        self.acq_seq_worker.finished.connect(self.acq_seq_thread.quit)
        self.acq_seq_thread.start()

    def stopAcqSequence(self):
        if self.acq_seq_worker:
            self.acq_seq_worker.stop()
            if self.acq_seq_thread:
                self.acq_seq_thread.quit()
                self.acq_seq_thread.wait()

    def cleanup(self):
        # Stop the acquisition read worker and close the serial ports.
        if self.acq_read_worker:
            self.acq_read_worker.stop()
        if self.acq_read_thread:
            self.acq_read_thread.quit()
            self.acq_read_thread.wait()
        self.motor_model.close()
        self.acq_model.close()
