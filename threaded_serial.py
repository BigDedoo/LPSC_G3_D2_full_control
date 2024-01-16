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


    def read_serial_data(self):
        try:
            while True:
                data = self.ser.readline().strip()
                if data:
                    # Put data in queue
                    self.data_queue.put(data.decode('utf-8'))
                    self.received_data_signal.emit(data.decode('utf-8'))
        except KeyboardInterrupt:
            print('Serial reading stopped.')
        finally:
            self.ser.close()

    def send_serial_data(self):
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
                    print(f'Received data: {self.received_data.decode("utf-8")}')

                # Wait for one second before sending the next command
                time.sleep(1)

        except KeyboardInterrupt:
            # Handle Ctrl+C to exit the loop
            print('Serial sending stopped.')

        finally:
            # Close the serial port when done
            self.ser.close()

    def run_acq(self):
        collecting_data = False
        collected_data = []

        while True:
            # Send 'A' command
            command = 'A'
            hex_command = ''.join(format(ord(char), '02X') for char in command)
            full_command = f"{hex_command}0D"
            command_bytes = bytes.fromhex(''.join(full_command.split()))
            self.ser.write(command_bytes)

            # Wait for a response from the serial port
            while not self.data_queue.empty():
                received_str = self.data_queue.get()
                print(f'Received data: {received_str}')

                if received_str == 'F':
                    collecting_data = True
                    # Send 'D' command
                    command = 'D'
                    hex_command = ''.join(format(ord(char), '02X') for char in command)
                    full_command = f"{hex_command}0D"
                    command_bytes = bytes.fromhex(''.join(full_command.split()))
                    self.ser.write(command_bytes)

                # Collect all data after 'F' is received
                if collecting_data:
                    collected_data.append(received_str)
                    print(collected_data)

                # Check if '00000000,00000000' is received, then stop collecting data
                if received_str == '00000000,00000000' and collecting_data:
                    # Write collected data to a CSV file
                    with open('received_data.csv', 'w', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(['Received Data'])
                        for data in collected_data:
                            writer.writerow([data])
                    break  # Stop the loop

            # Wait for 10 seconds before sending the next 'A' command
            time.sleep(10)

    def start_threads(self):
        # Create separate threads for reading and sending data
        read_thread = threading.Thread(target=self.read_serial_data)
        send_thread = threading.Thread(target=self.run_acq)

        # Start the threads
        read_thread.start()
        send_thread.start()
