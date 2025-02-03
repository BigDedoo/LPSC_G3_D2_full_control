# view/main_window.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTabWidget
)
from PyQt5.QtCore import pyqtSlot
import logging

logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    """
    The main user interface.
    """

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle("Modular Acquisition App")
        self.resize(800, 600)

        self.tab_widget = QTabWidget(self)

        # Tab 1: Commands
        self.command_tab = QWidget()
        self.setup_command_tab()

        # Tab 2: Acquisition Data (live view)
        self.data_tab = QWidget()
        self.setup_data_tab()

        self.tab_widget.addTab(self.command_tab, "Commands")
        self.tab_widget.addTab(self.data_tab, "Acquisition Data")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    def setup_command_tab(self):
        layout = QVBoxLayout()

        # Motor command controls
        motor_layout = QHBoxLayout()
        self.motor_command_input = QLineEdit()
        self.motor_send_button = QPushButton("Send Motor Command")
        motor_layout.addWidget(QLabel("Motor Command:"))
        motor_layout.addWidget(self.motor_command_input)
        motor_layout.addWidget(self.motor_send_button)

        # Acquisition command controls
        acq_layout = QHBoxLayout()
        self.acq_command_input = QLineEdit()
        self.acq_send_button = QPushButton("Send Acq Command")
        acq_layout.addWidget(QLabel("Acq Command:"))
        acq_layout.addWidget(self.acq_command_input)
        acq_layout.addWidget(self.acq_send_button)

        # Sequence control buttons
        seq_layout = QHBoxLayout()
        self.start_seq_button = QPushButton("Start Acq Sequence")
        self.stop_seq_button = QPushButton("Stop Acq Sequence")
        seq_layout.addWidget(self.start_seq_button)
        seq_layout.addWidget(self.stop_seq_button)

        # Output text areas
        self.motor_output = QTextEdit()
        self.motor_output.setReadOnly(True)
        self.acq_output = QTextEdit()
        self.acq_output.setReadOnly(True)

        layout.addLayout(motor_layout)
        layout.addLayout(acq_layout)
        layout.addLayout(seq_layout)
        layout.addWidget(QLabel("Motor Responses:"))
        layout.addWidget(self.motor_output)
        layout.addWidget(QLabel("Acquisition Data:"))
        layout.addWidget(self.acq_output)

        self.command_tab.setLayout(layout)

    def setup_data_tab(self):
        layout = QVBoxLayout()
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        layout.addWidget(QLabel("Live Acquisition Data:"))
        layout.addWidget(self.data_display)
        self.data_tab.setLayout(layout)

    def connect_signals(self):
        # Button click connections
        self.motor_send_button.clicked.connect(self.on_motor_send)
        self.acq_send_button.clicked.connect(self.on_acq_send)
        self.start_seq_button.clicked.connect(self.controller.startAcqSequence)
        self.stop_seq_button.clicked.connect(self.controller.stopAcqSequence)

        # Controller-to-view signal connections
        self.controller.motorResponseReceived.connect(self.update_motor_output)
        self.controller.acqDataReceived.connect(self.update_acq_output)
        self.controller.acqDataReceived.connect(self.update_data_display)
        self.controller.acqSequenceFinished.connect(self.on_sequence_finished)

    def on_motor_send(self):
        command = self.motor_command_input.text().strip()
        if command:
            self.controller.sendMotorCommand(command)

    def on_acq_send(self):
        command = self.acq_command_input.text().strip()
        if command:
            self.controller.sendAcqCommand(command)

    @pyqtSlot(str)
    def update_motor_output(self, response: str):
        self.motor_output.append(f"Motor Response: {response}")

    @pyqtSlot(str)
    def update_acq_output(self, data: str):
        self.acq_output.append(f"Acq Data: {data}")

    @pyqtSlot(str)
    def update_data_display(self, data: str):
        self.data_display.append(data)

    @pyqtSlot()
    def on_sequence_finished(self):
        self.acq_output.append("Acquisition Sequence Finished.")

    def closeEvent(self, event):
        # Ensure graceful shutdown
        self.controller.cleanup()
        event.accept()
