# controller/program_uploader_runnable.py

from PyQt5.QtCore import QRunnable, pyqtSlot
from controller.program_uploader import ProgramUploader

class ProgramUploaderRunnable(QRunnable):
    """
    QRunnable wrapper for the ProgramUploader.
    """
    def __init__(self, motor_model, file_path, program_name, progress_callback, error_callback, finished_callback):
        super().__init__()
        self.uploader = ProgramUploader(motor_model, file_path, program_name)
        self.uploader.progressUpdated.connect(progress_callback)
        self.uploader.errorOccurred.connect(error_callback)
        self.uploader.finished.connect(finished_callback)

    @pyqtSlot()
    def run(self):
        self.uploader.upload()
