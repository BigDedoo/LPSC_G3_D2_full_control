# ----- view/main_window.py -----

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTabWidget, QGridLayout
)
from PyQt5.QtCore import pyqtSlot
import logging

logger = logging.getLogger(__name__)

class MainWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.param_labels = {}  # to hold motor parameter display labels
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
        # Create a horizontal layout for two columns: left (controls & outputs) and right (motor parameters)
        main_layout = QHBoxLayout()

        # ---------------------- Left Column ----------------------
        left_layout = QVBoxLayout()

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

        # NEW: Stop X and Stop Y buttons
        stop_layout = QHBoxLayout()
        self.stop_x_button = QPushButton("Stop X")
        self.stop_y_button = QPushButton("Stop Y")
        stop_layout.addWidget(self.stop_x_button)
        stop_layout.addWidget(self.stop_y_button)

        # Motor Responses output
        self.motor_output = QTextEdit()
        self.motor_output.setReadOnly(True)
        # Acquisition Data output
        self.acq_output = QTextEdit()
        self.acq_output.setReadOnly(True)

        # Assemble left column layout
        left_layout.addLayout(motor_layout)
        left_layout.addLayout(acq_layout)
        left_layout.addLayout(seq_layout)
        left_layout.addLayout(stop_layout)   # <-- Added the new stop buttons here
        left_layout.addWidget(QLabel("Motor Responses:"))
        left_layout.addWidget(self.motor_output)
        left_layout.addWidget(QLabel("Acquisition Data:"))
        left_layout.addWidget(self.acq_output)

        # ---------------------- Right Column ----------------------
        right_layout = QVBoxLayout()

        # Create the "Poll Motor Parameters" button and place it above the parameters display.
        self.poll_motor_button = QPushButton("Poll Motor Parameters")

        # Create a grid layout for motor parameters display.
        motor_param_grid = QGridLayout()
        self.param_labels = {}  # Dictionary to store labels for each parameter.

        # Optional header row:
        motor_param_grid.addWidget(QLabel("Parameter"), 0, 0)
        motor_param_grid.addWidget(QLabel("X Motor"), 0, 1)
        motor_param_grid.addWidget(QLabel("Y Motor"), 0, 2)

        # Create 49 rows (parameters 1 through 49)
        for i in range(1, 50):
            label_param = QLabel(f"Param {i}:")
            label_x = QLabel("N/A")
            label_y = QLabel("N/A")
            self.param_labels[f"X{i}"] = label_x
            self.param_labels[f"Y{i}"] = label_y
            motor_param_grid.addWidget(label_param, i, 0)
            motor_param_grid.addWidget(label_x, i, 1)
            motor_param_grid.addWidget(label_y, i, 2)

        # Wrap the grid layout in a widget so it can be added to the right column.
        motor_param_widget = QWidget()
        motor_param_widget.setLayout(motor_param_grid)

        # Assemble right column: add the poll button and below it the motor parameters widget.
        right_layout.addWidget(self.poll_motor_button)
        right_layout.addWidget(motor_param_widget)

        # ---------------------- Combine Left and Right Columns ----------------------
        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addLayout(right_layout, stretch=2)

        self.command_tab.setLayout(main_layout)

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
        self.poll_motor_button.clicked.connect(self.on_poll_motor)
        self.stop_x_button.clicked.connect(self.on_stop_x)  # NEW connection for Stop X
        self.stop_y_button.clicked.connect(self.on_stop_y)  # NEW connection for Stop Y

        # Controller-to-view signal connections
        self.controller.motorResponseReceived.connect(self.update_motor_output)
        self.controller.acqDataReceived.connect(self.update_acq_output)
        self.controller.acqDataReceived.connect(self.update_data_display)
        self.controller.acqSequenceFinished.connect(self.on_sequence_finished)
        self.controller.motorParametersUpdated.connect(self.update_motor_parameters)

    def on_motor_send(self):
        command = self.motor_command_input.text().strip()
        if command:
            self.controller.sendMotorCommand(command)

    def on_acq_send(self):
        command = self.acq_command_input.text().strip()
        if command:
            self.controller.sendAcqCommand(command)

    def on_poll_motor(self):
        """Trigger the on-demand motor parameter poll."""
        self.controller.runMotorParameterPoller()

    @pyqtSlot()
    def on_stop_x(self):
        """Send the 'XS' command to stop motor X."""
        self.controller.sendMotorCommand("XS")

    @pyqtSlot()
    def on_stop_y(self):
        """Send the 'YS' command to stop motor Y."""
        self.controller.sendMotorCommand("YS")

    @pyqtSlot(str)
    def update_motor_output(self, response: str):
        self.motor_output.append(f"Motor Response: {response}")

    @pyqtSlot(str)
    def update_acq_output(self, data: str):
        self.acq_output.append(f"Acq Data: {data}")

    @pyqtSlot(str)
    def update_data_display(self, data: str):
        self.data_display.append(data)

    @pyqtSlot(dict)
    def update_motor_parameters(self, parameters: dict):
        for key, value in parameters.items():
            if key in self.param_labels:
                self.param_labels[key].setText(value)

    @pyqtSlot()
    def on_sequence_finished(self):
        self.acq_output.append("Acquisition Sequence Finished.")

    def closeEvent(self, event):
        self.controller.cleanup()
        event.accept()
