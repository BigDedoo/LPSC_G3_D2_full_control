# ----- acq_read_worker.py -----
from PyQt5.QtCore import QObject, pyqtSignal
import time

class AcqReadWorker(QObject):
    """
    A worker object that runs in a separate QThread to read
    serial data continuously from AcqModel.
    """
    dataReady = pyqtSignal(str)  # Emitted when new data is read.

    def __init__(self, acq_model, parent=None):
        super().__init__(parent)
        self.acq_model = acq_model
        self._running = True

    def run(self):
        """
        This method will be invoked when the thread starts.
        It continuously reads from the serial port until stopped.
        """
        while self._running:
            data = self.acq_model.read_serial_data()
            if data:
                self.dataReady.emit(data)
            time.sleep(0.01)  # small delay to avoid busy loop

    def stop(self):
        """Stop the reading loop gracefully."""
        self._running = False
