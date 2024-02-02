import sys
import os
import threading
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import qdarkstyle

from pyqt_led import Led
from motor_model import MotorModel
from motor_controler import MotorControler
from acq_model import AcqModel
from acq_controller import AcqController
from data_management import *

from PyQt5 import QtWidgets
from PyQt5.QtCore import QUrl, QThread
from PyQt5.QtWidgets import QHBoxLayout, QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QTextEdit, \
    QTabWidget
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

        #self.threaded_serial.start_writing()

        self.init_ui()

    def init_ui(self):
        self.setup_widgets()
        self.setup_tabs()
        self.setup_layouts()
        self.setup_connections()
        self.finalize_ui()

    def setup_widgets(self):
        # Initialize all widgets
        self.label = QLabel('Enter text command:')
        self.entry = QLineEdit()
        self.send_button = QPushButton('Send Command')
        self.text_output = QTextEdit()
        self.thread_output = QTextEdit()
        # Create new QTextEdits for additional information
        self.max_x_current_edit = QTextEdit()
        self.max_y_current_edit = QTextEdit()
        self.max_density_edit = QTextEdit()
        self.acquisition_status_edit = QTextEdit()

        # Initialize the LED widget for acquisition status
        self.acquisition_status_led = Led(self, on_color=Led.green, off_color=Led.red)
        self.acquisition_status_led.turn_off()

        self.plotly_view = QWebEngineView()
        self.button_acq = QPushButton('Acquisition')
        self.plot_button = QPushButton('Plot Data')

        button_size = 70  # Size in pixels, adjust as needed
        self.button_acq.setFixedSize(button_size, button_size)  # Set as square
        self.plot_button.setFixedSize(button_size, button_size)  # Set as square


    def setup_tabs(self):
        # Set up tabs
        self.tab_widget = QTabWidget()
        self.main_tab = QWidget()
        self.measurements_tab = QWidget()

    def setup_layouts(self):
        # Set up layouts for each tab
        self.setup_main_tab_layout()
        self.setup_measurements_tab_layout()

    def setup_main_tab_layout(self):
        # Layout for main tab
        self.main_layout = QVBoxLayout(self.main_tab)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.entry)
        self.main_layout.addWidget(self.send_button)
        self.main_layout.addWidget(self.text_output)
        self.main_layout.addWidget(self.thread_output)

    def setup_measurements_tab_layout(self):
        # Layout for measurements tab
        self.measurements_layout = QVBoxLayout(self.measurements_tab)

        self.plotly_layout = QVBoxLayout()
        self.plotly_layout.addWidget(self.plotly_view)



        # Vertical layout for the new QTextEdits
        self.info_layout = QVBoxLayout()

        # Set a maximum width for each QTextEdit
        max_text_edit_width = 100  # Maximum width in pixels
        max_text_edit_height = 50  # Maximum width in pixels


        self.max_x_current_edit.setMaximumWidth(max_text_edit_width)
        self.max_y_current_edit.setMaximumWidth(max_text_edit_width)
        self.max_density_edit.setMaximumWidth(max_text_edit_width)
        self.acquisition_status_edit.setMaximumWidth(max_text_edit_width)

        self.max_x_current_edit.setMaximumHeight(max_text_edit_height)
        self.max_y_current_edit.setMaximumHeight(max_text_edit_height)
        self.max_density_edit.setMaximumHeight(max_text_edit_height)
        self.acquisition_status_edit.setMaximumHeight(max_text_edit_height)


        self.info_layout.addWidget(QLabel("Maximum X Current"))
        self.info_layout.addWidget(self.max_x_current_edit, 1)
        self.info_layout.addWidget(QLabel("Maximum Y Current"))
        self.info_layout.addWidget(self.max_y_current_edit, 1)
        self.info_layout.addWidget(QLabel("Maximum Density"))
        self.info_layout.addWidget(self.max_density_edit, 1)
        self.info_layout.addWidget(QLabel("Acquisition Status"))
        self.info_layout.addWidget(self.acquisition_status_edit, 1)
        self.plotly_view.setMinimumSize(500, 400)

        self.info_layout.addWidget(QLabel("Acquisition Status"))
        self.info_layout.addWidget(self.acquisition_status_led)  # Add LED widget

        # Horizontal layout for Plotly graph and info text edits
        self.info_and_graph_layout = QHBoxLayout()
        self.info_and_graph_layout.addLayout(self.plotly_layout, 4)  # 80% space
        self.info_and_graph_layout.addLayout(self.info_layout, 1)  # 20% space

        # Layout for buttons
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.button_acq)
        self.buttons_layout.addWidget(self.plot_button)

        # Add the combined layout and buttons layout to the measurements layout
        self.measurements_layout.addLayout(self.info_and_graph_layout)
        self.measurements_layout.addLayout(self.buttons_layout)



    def setup_connections(self):
        # Connect signals and slots
        self.send_button.clicked.connect(self.on_send_button_click)
        self.button_acq.clicked.connect(self.threaded_serial.start_acq_collect_sequence)
        self.plot_button.clicked.connect(self.plot_data_from_csv)

    def finalize_ui(self):
        # Add tabs to tab widget and set main layout
        self.tab_widget.addTab(self.measurements_tab, "Main")
        self.tab_widget.addTab(self.main_tab, "Serial com lurker")

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        # Set up the main window
        self.setWindowTitle('Big peepee python app')
        self.resize(800, 600)
        self.show()

    def plot_data_from_csv(self, csv_file_path='data/collected_data_centered.csv'):
        # Read and convert the CSV files
        #df1 = read_csv_to_dataframe('data/modified_data_1.csv')
        #df2 = read_csv_to_dataframe('data/modified_data_2.csv')

        df1 = read_and_convert_csv('data/collected_data_centered.csv').iloc[:, [1]]
        df2 = read_and_convert_csv('data/collected_data_centered_2.csv').iloc[:, [1]]

        #df1 = df1.iloc[:,1:]
        df1.columns = ['Y_1']
        #df2 = df2.iloc[:,1:]
        df2.columns = ['Y_2']
        df = pd.concat([df1, df2], axis=1)

        if df.shape[1] != 2:
            raise ValueError("DataFrame must have exactly two columns")

        num_rows = df.shape[0]
        # Initialize a 2D array for the 3D map data
        map_data = np.zeros((num_rows, num_rows))

        # Calculate the sum for each combination of row numbers
        for i in range(num_rows):
            print(i)
            for j in range(num_rows):
                map_data[i, j] = df.iloc[i, 0] + df.iloc[j, 1]

        # Create the 3D map
        fig = go.Figure(data=[go.Surface(z=map_data, x=np.arange(num_rows), y=np.arange(num_rows))])
        fig.update_layout(
            title='Beam density in the XY plane',
            scene=dict(
                xaxis_title='X (mm)',
                yaxis_title='Y (mm)',
                zaxis_title='Density (muA)'
            )
        )

        plotly_html_path = os.path.abspath('plotly_graph.html')
        plotly_html_div = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')

        fig.write_html(plotly_html_path)
        self.plotly_view.setHtml(plotly_html_div)
        max_values = find_max_values(df)
        self.max_x_current_edit.setText(str(max_values[0]))
        self.max_y_current_edit.setText(str(max_values[1]))
        self.max_density_edit.setText(str(max_values[2]))

    def handle_ack(self, response):
        # Handle ACK response
        # Extract the content between <ACK> and <ETX>
        content = response.split('<ACK>')[1].split('<ETX>')[0]

        # Modify the instance variables accordingly
        self.ack_response = content
        self.nak_response = None

    def handle_nak(self, response):
        # Handle NAK response
        # Modify the instance variables accordingly
        self.ack_response = None
        self.nak_response = "<NAK>"

    def on_send_button_click(self):
        # Get the user-provided text from the entry field
        user_text_command = self.entry.text()

        # Send the command to the serial port
        self.serial_communication.handle_user_input(user_text_command)

        if self.ack_response is not None:
            self.text_output.append(f"Command '{user_text_command}': \n{self.ack_response}\n")
        elif self.nak_response:
            self.text_output.append(f"Command '{user_text_command}' not recognized\n")

    def handle_received_data(self, data):
        # Handle received data and update the GUI
        self.thread_output.append(f'Received data: {data}')
        if data == 'B':
            self.acquisition_status_led.turn_on()
            self.acquisition_status_edit.setText('Busy')
        elif data == 'F':
            self.acquisition_status_led.turn_off()
            self.acquisition_status_edit.setText('Dumping')
        elif data == '00000000,00000000':
            self.acquisition_status_edit.setText('Done')


    def init_plotly_graph(self):
        plotly_html_path = os.path.abspath('plotly_graph.html')
        # Display the HTML file in the QWebEngineView
        self.plotly_view.setUrl(QUrl.fromLocalFile(plotly_html_path))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
