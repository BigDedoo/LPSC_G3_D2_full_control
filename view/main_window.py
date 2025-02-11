# view/main_window.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTabWidget, QGridLayout, QFileDialog, QGroupBox
)
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView  # For Plotly graphs
import logging
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.offline as pyo

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
        self.resize(1000, 700)

        self.tab_widget = QTabWidget(self)

        # Tab 1: Commands remains the same.
        self.command_tab = QWidget()
        self.setup_command_tab()

        # Tab 2: Graph (Acquired Data Graphs)
        self.graph_tab = QWidget()
        self.setup_graph_tab()

        # Tab 3: Beam Shape (3D reconstruction from X & Y data)
        self.beam_tab = QWidget()
        self.setup_beam_tab()

        self.tab_widget.addTab(self.command_tab, "Commands")
        self.tab_widget.addTab(self.graph_tab, "Graphs")
        self.tab_widget.addTab(self.beam_tab, "Beam Shape")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    def setup_command_tab(self):
        # Create the overall layout for the Commands tab.
        main_layout = QHBoxLayout()

        # ---------------------- Left Column ----------------------
        left_layout = QVBoxLayout()

        # --- Motor command controls ---
        motor_layout = QHBoxLayout()
        self.motor_command_input = QLineEdit()
        self.motor_send_button = QPushButton("Send Motor Command")
        motor_layout.addWidget(QLabel("Motor Command:"))
        motor_layout.addWidget(self.motor_command_input)
        motor_layout.addWidget(self.motor_send_button)

        # --- Acquisition command controls ---
        acq_layout = QHBoxLayout()
        self.acq_command_input = QLineEdit()
        self.acq_send_button = QPushButton("Send Acq Command")
        acq_layout.addWidget(QLabel("Acq Command:"))
        acq_layout.addWidget(self.acq_command_input)
        acq_layout.addWidget(self.acq_send_button)

        # --- Sequence control buttons ---
        seq_layout = QHBoxLayout()
        self.start_seq_button = QPushButton("Start Acq Sequence")
        self.stop_seq_button = QPushButton("Stop Acq Sequence")
        seq_layout.addWidget(self.start_seq_button)
        seq_layout.addWidget(self.stop_seq_button)

        # --- New: Poll Acq Data button ---
        poll_acq_layout = QHBoxLayout()
        self.poll_acq_button = QPushButton("Poll Acq Data")
        poll_acq_layout.addWidget(self.poll_acq_button)

        # --- Stop X and Stop Y buttons ---
        stop_layout = QHBoxLayout()
        self.stop_x_button = QPushButton("Stop X")
        self.stop_y_button = QPushButton("Stop Y")
        stop_layout.addWidget(self.stop_x_button)
        stop_layout.addWidget(self.stop_y_button)

        # --- Motor Responses output ---
        self.motor_output = QTextEdit()
        self.motor_output.setReadOnly(True)
        # --- Acquisition Data output ---
        self.acq_output = QTextEdit()
        self.acq_output.setReadOnly(True)

        # --- Program Upload group ---
        prog_upload_group = QGroupBox("Program Upload")
        prog_upload_layout = QHBoxLayout()
        self.prog_name_input = QLineEdit()
        self.prog_name_input.setPlaceholderText("Program Name (8 chars)")
        self.upload_prog_button = QPushButton("Upload Program")
        prog_upload_layout.addWidget(QLabel("Program Name:"))
        prog_upload_layout.addWidget(self.prog_name_input)
        prog_upload_layout.addWidget(self.upload_prog_button)
        prog_upload_group.setLayout(prog_upload_layout)

        # Assemble left column layout
        left_layout.addLayout(motor_layout)
        left_layout.addLayout(acq_layout)
        left_layout.addLayout(seq_layout)
        left_layout.addLayout(poll_acq_layout)  # Added Poll Acq Data button
        left_layout.addLayout(stop_layout)
        left_layout.addWidget(QLabel("Motor Responses:"))
        left_layout.addWidget(self.motor_output)
        left_layout.addWidget(QLabel("Acq Data:"))
        left_layout.addWidget(self.acq_output)
        left_layout.addWidget(prog_upload_group)

        # ---------------------- Right Column ----------------------
        right_layout = QVBoxLayout()

        # Create the "Poll Motor Parameters" button
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

        motor_param_widget = QWidget()
        motor_param_widget.setLayout(motor_param_grid)

        right_layout.addWidget(self.poll_motor_button)
        right_layout.addWidget(motor_param_widget)

        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addLayout(right_layout, stretch=2)

        self.command_tab.setLayout(main_layout)

    def setup_graph_tab(self):
        """
        Set up the Graph tab to display two Plotly graphs (one for acquired_data_X.csv and one for acquired_data_Y.csv).
        """
        layout = QVBoxLayout()
        self.graph_view_x = QWebEngineView()
        self.graph_view_y = QWebEngineView()
        layout.addWidget(QLabel("Graph for Acquired Data X"))
        layout.addWidget(self.graph_view_x, stretch=1)
        layout.addWidget(QLabel("Graph for Acquired Data Y"))
        layout.addWidget(self.graph_view_y, stretch=1)
        self.graph_tab.setLayout(layout)
        self.plot_graphs()

    def setup_beam_tab(self):
        """
        Set up the Beam Shape tab to display a 3D surface plot of the beam.
        """
        layout = QVBoxLayout()
        self.plot_beam_button = QPushButton("Plot Beam Shape")
        layout.addWidget(self.plot_beam_button)
        self.beam_view = QWebEngineView()
        layout.addWidget(self.beam_view, stretch=1)
        self.beam_tab.setLayout(layout)
        self.plot_beam_button.clicked.connect(self.plot_beam_shape)

    def plot_graphs(self):
        try:
            from utils.conversions import hex_to_current
            import numpy as np
            df_x = pd.read_csv("acquired_data_X.csv", header=None)
            df_y = pd.read_csv("acquired_data_Y.csv", header=None)
            x_current = df_x[0].apply(lambda hex_val: hex_to_current(str(hex_val))).to_numpy()
            y_current = df_y[0].apply(lambda hex_val: hex_to_current(str(hex_val))).to_numpy()
            fig_x = go.Figure(data=go.Scatter(
                x=np.arange(len(x_current)),
                y=x_current,
                mode='lines',
                name='X Motor Data'
            ))
            fig_x.update_layout(
                title="Acquired Current Data for X Motor",
                xaxis_title="Index",
                yaxis_title="Current (A)"
            )
            fig_y = go.Figure(data=go.Scatter(
                x=np.arange(len(y_current)),
                y=y_current,
                mode='lines',
                name='Y Motor Data'
            ))
            fig_y.update_layout(
                title="Acquired Current Data for Y Motor",
                xaxis_title="Index",
                yaxis_title="Current (A)"
            )
            html_x = pyo.plot(fig_x, include_plotlyjs='cdn', output_type='div')
            html_y = pyo.plot(fig_y, include_plotlyjs='cdn', output_type='div')
            self.graph_view_x.setHtml(html_x)
            self.graph_view_y.setHtml(html_y)
        except Exception as e:
            logger.error(f"Error plotting graphs: {e}")

    @pyqtSlot()
    def plot_beam_shape(self):
        try:
            from utils.conversions import hex_to_current
            df_x = pd.read_csv("acquired_data_X.csv", header=None)
            df_y = pd.read_csv("acquired_data_Y.csv", header=None)
            x_profile = df_x[0].apply(lambda hex_val: hex_to_current(str(hex_val))).to_numpy()
            y_profile = df_y[0].apply(lambda hex_val: hex_to_current(str(hex_val))).to_numpy()
            step_size = 0.5
            x_axis = np.arange(len(x_profile)) * step_size
            y_axis = np.arange(len(y_profile)) * step_size
            Z = np.outer(x_profile, y_profile)
            heatmap = go.Heatmap(
                z=Z,
                x=x_axis,
                y=y_axis,
                colorscale='Viridis'
            )
            fig = go.Figure(data=[heatmap])
            fig.update_layout(
                title="Beam Current Heat Map",
                xaxis_title="X Position (mm)",
                yaxis_title="Y Position (mm)",
                autosize=True,
                width=800,
                height=800,
                margin=dict(l=65, r=50, b=65, t=90)
            )
            html_heatmap = pyo.plot(fig, include_plotlyjs='cdn', output_type='div')
            self.beam_view.setHtml(html_heatmap)
        except Exception as e:
            logger.error(f"Error plotting beam shape: {e}")

    def connect_signals(self):
        self.motor_send_button.clicked.connect(self.on_motor_send)
        self.acq_send_button.clicked.connect(self.on_acq_send)
        self.start_seq_button.clicked.connect(self.controller.startAcqSequence)
        self.stop_seq_button.clicked.connect(self.controller.stopAcqSequence)
        self.poll_motor_button.clicked.connect(self.on_poll_motor)
        self.poll_acq_button.clicked.connect(self.on_poll_acq)  # Connect new Poll Acq Data button
        self.stop_x_button.clicked.connect(self.on_stop_x)
        self.stop_y_button.clicked.connect(self.on_stop_y)
        self.upload_prog_button.clicked.connect(self.on_program_upload)
        self.controller.motorResponseReceived.connect(self.update_motor_output)
        self.controller.acqDataReceived.connect(self.update_acq_output)
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

    def on_poll_acq(self):
        """Trigger acquisition data polling and save the data to requested_data.csv."""
        self.acq_output.append("Starting Acquisition Data Polling...")
        self.controller.startAcqDataPoller()

    @pyqtSlot()
    def on_stop_x(self):
        self.controller.sendMotorCommand("XS")

    @pyqtSlot()
    def on_stop_y(self):
        self.controller.sendMotorCommand("YS")

    @pyqtSlot(str)
    def update_motor_output(self, response: str):
        self.motor_output.append(f"Motor Response: {response}")

    @pyqtSlot(str)
    def update_acq_output(self, data: str):
        self.acq_output.append(f"Acq Data: {data}")

    @pyqtSlot(dict)
    def update_motor_parameters(self, parameters: dict):
        for key, value in parameters.items():
            if key in self.param_labels:
                self.param_labels[key].setText(value)

    @pyqtSlot()
    def on_sequence_finished(self):
        self.acq_output.append("Acquisition Sequence Finished.")

    @pyqtSlot()
    def on_program_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Program File", "", "Text Files (*.txt)"
        )
        if file_path:
            prog_name = self.prog_name_input.text().strip()
            if len(prog_name) == 0:
                self.acq_output.append("Please enter a program name (8 characters).")
                return
            if len(prog_name) > 8:
                prog_name = prog_name[:8]
            self.acq_output.append(f"Uploading program '{prog_name}' from {file_path}...")
            self.controller.startProgramUpload(file_path, prog_name)

    def closeEvent(self, event):
        self.controller.cleanup()
        event.accept()
