import threading
from PyQt5.QtCore import pyqtSignal, QObject
import serial
import time

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

    def read_serial_data(self):
        try:
            while True:
                # Read data from the serial port
                data = self.ser.readline().strip()

                # Check if there's any data
                if data:
                    with self.data_received:
                        self.received_data = data
                        self.data_received.notify()
                        # Emit the received data to str
                        self.received_data_signal.emit(data.decode('utf-8'))

        except KeyboardInterrupt:
            # Handle Ctrl+C to exit the loop
            print('Serial reading stopped.')

        finally:
            # Close the serial port when done
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

    def start_threads(self):
        # Create separate threads for reading and sending data
        read_thread = threading.Thread(target=self.read_serial_data)
        send_thread = threading.Thread(target=self.send_serial_data)

        # Start the threads
        read_thread.start()
        send_thread.start()
