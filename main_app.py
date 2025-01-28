# ----- main_app.py -----

import sys
import os
import threading
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import qdarkstyle

from pyqt_led import Led
from motor_controler import MotorControler
from acq_controller import AcqController
from data_management import *

from PyQt5 import QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import (
    QHBoxLayout, QApplication, QWidget, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QTextEdit, QTabWidget
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.offline as py_offline

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.serial_communication = MotorControler()
        self.serial_communication.ACK_SIGNAL.connect(self.handle_ack)
        self.serial_communication.NAK_SIGNAL.connect(self.handle_nak)

        self.ack_response = None
        self.nak_response = None

        self.threaded_serial = AcqController()
        self.threaded_serial.acq_received_data_signal.connect(self.handle_received_data)

        # Start threaded serial communication
        self.threaded_serial.start_reading()

        self.init_ui()

    def init_ui(self):
        self.setup_widgets()
        self.setup_tabs()
        self.setup_layouts()
        self.setup_connections()
        self.finalize_ui()

    def setup_widgets(self):
        self.label = QLabel('Enter text command:')
        self.entry = QLineEdit()
        self.send_button = QPushButton('Send Command')
        self.text_output = QTextEdit()
        self.thread_output = QTextEdit()

        self.max_x_current_edit = QTextEdit()
        self.max_y_current_edit = QTextEdit()
        self.max_density_edit = QTextEdit()
        self.acquisition_status_edit = QTextEdit()

        self.acquisition_status_led = Led(self, on_color=Led.green, off_color=Led.red)
        self.acquisition_status_led.turn_off()

        self.plotly_view = QWebEngineView()
        self.button_acq = QPushButton('Acquisition')
        self.plot_button = QPushButton('Plot Data')

        button_size = 70
        self.button_acq.setFixedSize(button_size, button_size)
        self.plot_button.setFixedSize(button_size, button_size)

    def setup_tabs(self):
        self.tab_widget = QTabWidget()
        self.main_tab = QWidget()
        self.measurements_tab = QWidget()

    def setup_layouts(self):
        self.setup_main_tab_layout()
        self.setup_measurements_tab_layout()

    def setup_main_tab_layout(self):
        self.main_layout = QVBoxLayout(self.main_tab)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.entry)
        self.main_layout.addWidget(self.send_button)
        self.main_layout.addWidget(self.text_output)
        self.main_layout.addWidget(self.thread_output)

    def setup_measurements_tab_layout(self):
        self.measurements_layout = QVBoxLayout(self.measurements_tab)

        self.plotly_layout = QVBoxLayout()
        self.plotly_layout.addWidget(self.plotly_view)

        self.info_layout = QVBoxLayout()
        max_text_edit_width = 100
        max_text_edit_height = 50

        for edit in [self.max_x_current_edit, self.max_y_current_edit,
                     self.max_density_edit, self.acquisition_status_edit]:
            edit.setMaximumWidth(max_text_edit_width)
            edit.setMaximumHeight(max_text_edit_height)

        self.info_layout.addWidget(QLabel("Maximum X Current"))
        self.info_layout.addWidget(self.max_x_current_edit)
        self.info_layout.addWidget(QLabel("Maximum Y Current"))
        self.info_layout.addWidget(self.max_y_current_edit)
        self.info_layout.addWidget(QLabel("Maximum Density"))
        self.info_layout.addWidget(self.max_density_edit)
        self.info_layout.addWidget(QLabel("Acquisition Status"))
        self.info_layout.addWidget(self.acquisition_status_edit)
        self.info_layout.addWidget(QLabel("Acquisition Status"))
        self.info_layout.addWidget(self.acquisition_status_led)

        self.plotly_view.setMinimumSize(500, 400)

        self.info_and_graph_layout = QHBoxLayout()
        self.info_and_graph_layout.addLayout(self.plotly_layout, 4)
        self.info_and_graph_layout.addLayout(self.info_layout, 1)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.button_acq)
        self.buttons_layout.addWidget(self.plot_button)

        self.measurements_layout.addLayout(self.info_and_graph_layout)
        self.measurements_layout.addLayout(self.buttons_layout)

    def setup_connections(self):
        self.send_button.clicked.connect(self.on_send_button_click)
        self.button_acq.clicked.connect(self.threaded_serial.start_acq_collect_sequence)
        self.plot_button.clicked.connect(self.plot_data_from_csv)

    def finalize_ui(self):
        self.tab_widget.addTab(self.measurements_tab, "Main")
        self.tab_widget.addTab(self.main_tab, "Serial com lurker")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        self.setWindowTitle('Big peepee python app')
        self.resize(800, 600)
        self.show()

    def plot_data_from_csv(self, csv_file_path='data/collected_data_centered.csv'):
        # Implementation for plotting the data
        df1 = read_and_convert_csv('data/collected_data_centered.csv').iloc[:, [1]]
        df2 = read_and_convert_csv('data/collected_data_centered_2.csv').iloc[:, [1]]

        df1.columns = ['Y_1']
        df2.columns = ['Y_2']
        df = pd.concat([df1, df2], axis=1)

        if df.shape[1] != 2:
            raise ValueError("DataFrame must have exactly two columns")

        num_rows = df.shape[0]
        map_data = np.zeros((num_rows, num_rows))

        for i in range(num_rows):
            for j in range(num_rows):
                map_data[i, j] = df.iloc[i, 0] + df.iloc[j, 1]

        fig = go.Figure(data=[go.Surface(z=map_data,
                                         x=np.arange(num_rows),
                                         y=np.arange(num_rows))])
        fig.update_layout(
            title='Beam density in the XY plane',
            scene=dict(
                xaxis_title='X (mm)',
                yaxis_title='Y (mm)',
                zaxis_title='Density (muA)'
            )
        )

        plotly_html_div = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
        self.plotly_view.setHtml(plotly_html_div)

        max_values = find_max_values(df)
        self.max_x_current_edit.setText(str(max_values[0]))
        self.max_y_current_edit.setText(str(max_values[1]))
        self.max_density_edit.setText(str(max_values[2]))

    def handle_ack(self, response):
        content = response.split('<ACK>')[1].split('<ETX>')[0]
        self.ack_response = content
        self.nak_response = None

    def handle_nak(self, response):
        self.ack_response = None
        self.nak_response = "<NAK>"

    def on_send_button_click(self):
        user_text_command = self.entry.text()
        self.serial_communication.handle_user_input(user_text_command)

        if self.ack_response is not None:
            self.text_output.append(f"Command '{user_text_command}': \n{self.ack_response}\n")
        elif self.nak_response:
            self.text_output.append(f"Command '{user_text_command}' not recognized\n")

    def handle_received_data(self, data):
        self.thread_output.append(f'Received data: {data}')
        if data == 'B':
            self.acquisition_status_led.turn_on()
            self.acquisition_status_edit.setText('Busy')
        elif data == 'F':
            self.acquisition_status_led.turn_off()
            self.acquisition_status_edit.setText('Dumping')
        elif data == '00000000,00000000':
            self.acquisition_status_edit.setText('Done')

    def closeEvent(self, event):
        # Make sure we stop the reading thread gracefully.
        self.threaded_serial.stop_reading()
        event.accept()  # or event.ignore() if needed


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
