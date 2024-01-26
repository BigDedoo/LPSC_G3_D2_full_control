import sys
import os
import threading
import pandas as pd
import plotly.graph_objs as go

from motor_model import MotorModel
from motor_controler import MotorControler
from acq_model import AcqModel
from acq_controller import AcqController


from PyQt5.QtCore import QUrl, QThread
from PyQt5.QtWidgets import QHBoxLayout, QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QTextEdit, \
    QTabWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView

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
        # Widgets
        self.label = QLabel('Enter text command:')
        self.entry = QLineEdit()
        self.send_button = QPushButton('Send Command')
        self.text_output = QTextEdit()
        self.thread_output = QTextEdit()

        # Set up tabs
        self.tab_widget = QTabWidget()
        self.main_tab = QWidget()
        self.measurements_tab = QWidget()
        self.plotly_widget = QWidget()

        # Layouts for tabs
        self.main_layout = QVBoxLayout(self.main_tab)
        self.measurements_layout = QVBoxLayout(self.measurements_tab)
        self.plotly_layout = QVBoxLayout(self.plotly_widget)

        # Plotly graph
        self.plotly_view = QWebEngineView()
        self.plotly_widget = QWidget()

        # Layout for main tab
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.entry)
        self.main_layout.addWidget(self.send_button)
        self.main_layout.addWidget(self.text_output)
        self.main_layout.addWidget(self.thread_output)

        # Layout for measurements tab
        self.measurements_push_layout = QVBoxLayout()

        # Add four push buttons to the measurements tab
        self.button_acq = QPushButton('Seq')

        self.measurements_push_layout.addWidget(self.button_acq)

        # Connect buttons directly to the acq_sequence method
        self.button_acq.clicked.connect(self.threaded_serial.start_acq_collect_sequence)

        # Add the layout to the measurements tab
        self.measurements_layout.addLayout(self.measurements_push_layout)

        # Layout for Plotly graph
        self.plotly_layout = QVBoxLayout(self.plotly_widget)
        self.plotly_layout.addWidget(self.plotly_view)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.main_tab, "Main")
        self.tab_widget.addTab(self.measurements_tab, "Measurements")
        self.tab_widget.addTab(self.plotly_widget, "Plotly Graph")

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)

        # Set the layout for the main window
        self.setLayout(main_layout)

        # Connect the button click event to the function
        self.send_button.clicked.connect(self.on_send_button_click)

        # Create a new button for plotting
        self.plot_button = QPushButton('Plot Data')
        self.plot_button.clicked.connect(self.plot_data_from_csv)
        self.measurements_layout.addWidget(self.plot_button)

        # Set up the main window
        self.setWindowTitle('Serial Port Communication')

        # Resize the window to 800x600 pixels
        self.resize(800, 600)

        # Show the window
        self.show()

        # Example: Initialize Plotly graph
        self.init_plotly_graph()
        #self.plot_data_from_csv().

    def plot_data_from_csv(self, csv_file_path='received_data.csv'):
        # Read the CSV file into a DataFrame
        df = pd.read_csv(csv_file_path, header=None)

        # Convert each value from hexadecimal to decimal
        df_decimal = df.map(lambda x: int(str(x), 16))

        # Create a Plotly graph
        fig = go.Figure()

        # Assuming each column is a separate set of data
        for col in df.columns:
            fig.add_trace(go.Scatter(y=df_decimal[col], mode='lines', name=f'Set {col + 1}'))

        # Update layout
        fig.update_layout(
            title='Data Sets from CSV',
            xaxis_title='Index',
            yaxis_title='Value',
            legend_title='Data Sets'
        )


        plotly_html_path = os.path.abspath('plotly_graph.html')
        fig.write_html(plotly_html_path)

        # Display the HTML file in the QWebEngineView
        self.plotly_view.setUrl(QUrl.fromLocalFile(plotly_html_path))



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

    def init_plotly_graph(self):
        # Read data from a csv
        z_data = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/api_docs/mt_bruno_elevation.csv')

        fig = go.Figure(data=[go.Surface(z=z_data.values)])

        fig.update_layout(title='Mt Bruno Elevation', autosize=False,
                          width=500, height=500,
                          margin=dict(l=65, r=50, b=65, t=90))

        # Save the Plotly graph as an HTML file
        plotly_html_path = os.path.abspath('plotly_graph.html')
        fig.write_html(plotly_html_path)

        # Display the HTML file in the QWebEngineView
        self.plotly_view.setUrl(QUrl.fromLocalFile(plotly_html_path))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
