import threading
from PyQt5.QtCore import pyqtSignal, QObject
import serial
import time
import csv
import queue

class ThreadedSerial(QObject):
    received_data_signal = pyqtSignal(str)

    def __init__(self, com_port, baud_rate):
        super().__init__()

        self.COM_PORT = com_port
        self.BAUD_RATE = baud_rate
        self.TIMEOUT = 1

        # Initialize the serial port
        self.ser = serial.Serial(self.COM_PORT, self.BAUD_RATE, timeout=self.TIMEOUT)

        # Create a condition variable to signal when data is received
        self.data_received = threading.Condition()

        # Shared variable to store the received data
        self.received_data = None

        # Queue for storing received data
        self.data_queue = queue.Queue()

        self.read_thread = threading.Thread(target=self.read_serial_data)
        self.acq_thread = threading.Thread(target=self.run_acq)
        self.new_data_available = False


    def read_serial_data(self):
        try:
            while True:
                # Read data from the serial port
                self.received_data = self.ser.readline().strip()

                # Check if there's any data
                if self.received_data:
                    with self.data_received:
                        self.data_received.notify()
                    # Put data in queue
                    self.data_queue.put(self.received_data.decode('utf-8'))
                    self.received_data_signal.emit(self.received_data.decode('utf-8'))

        except KeyboardInterrupt:
            # Handle Ctrl+C to exit the loop
            print('Serial reading stopped.')

        finally:
            # Close the serial port when done
            self.ser.close()

    def send_serial_data(self, command):
        # Convert the command to hexadecimal and append carriage return
        hex_command = ''.join(format(ord(char), '02X') for char in command)
        full_command = f"{hex_command}0D"
        command_bytes = bytes.fromhex(''.join(full_command.split()))

        # Send the command
        self.ser.write(command_bytes)

        # Wait for a response from the serial port
        with self.data_received:
            self.data_received.wait()
            print(f'Received data: {self.received_data.decode("utf-8")}')

    def run_acq(self):
        collecting_data = False
        collected_data = []

        while True:
            if not collecting_data:
                # Send 'A' command
                self.send_serial_data('A')

            # Wait for data to be available in the data_queue
            while self.data_queue.empty():
                time.sleep(1)

            while not self.data_queue.empty():
                received_str = self.data_queue.get()
                if received_str == 'F':
                    collecting_data = True
                    self.send_serial_data('D')  # Send 'D' command after receiving 'F'
                    continue  # Skip appending 'F' to collected_data

                if received_str == '00000000,00000000' and collecting_data:
                    try:
                        # Write the collected data to a CSV file
                        with open('received_data.csv', 'w', newline='') as file:
                            writer = csv.writer(file)
                            for data in collected_data:
                                data_list = data.split(',')
                                writer.writerow(data_list)  # Write the list of values
                        print("CSV file written successfully.")
                        return  # Exit the method after writing to CSV
                    except Exception as e:
                        print(f"Error writing to CSV file: {e}")

                if collecting_data:
                    collected_data.append(received_str)  # Collect the data
            """
            # Reset for the next cycle
            collecting_data = False
            collected_data = []
            """

    def test(self):
        try:
            while True:
                # Automatically send 'R' command every second
                command = 'R'
                hex_command = ''.join(format(ord(char), '02X') for char in command)
                full_command = f"{hex_command}0D"
                command_bytes = bytes.fromhex(''.join(full_command.split()))

                self.ser.write(command_bytes)

                # Wait for a response from the serial port
                with self.data_received:
                    self.data_received.wait()

                # Wait for one second before sending the next command
                time.sleep(1)

        except KeyboardInterrupt:
            # Handle Ctrl+C to exit the loop
            print('Serial sending stopped.')

        finally:
            # Close the serial port when done
            self.ser.close()
