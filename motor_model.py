from PyQt5.QtCore import pyqtSignal, QObject
import serial

class MotorModel(QObject):

    def __init__(self, COM_PORT, BAUD_RATE, TIMEOUT):
        super().__init__()

        # Initialize the serial port
        self.ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)

    def send_command(self, text_command):
        try:
            # Convert text_command to hexadecimal representation
            hex_command = ''.join(format(ord(char), '02X') for char in text_command)

            # Construct the full command with start (STX), controller address, hex command, and end (ETX)
            full_command = f"02 30 {hex_command} 03"

            # Convert the full command to bytes and send it over the serial port
            command_bytes = bytes.fromhex(''.join(full_command.split()))
            self.ser.write(command_bytes)

            print(f"Command '{full_command}' sent to {self.ser.port} successfully.")

            # Read the response from the serial port and format it for easier interpretation
            response = self.ser.readline().strip()
            response_repr = repr(response)[2:-1].replace('\\x02', '<STX>').replace('\\x06', '<ACK>') \
                .replace('\\x03', '<ETX>').replace('\\x15', '<NAK>')
            return response_repr
            # Emit signals based on the type of response received

        except serial.SerialException as e:
            print(f"Error: {e}")

    def close_serial_port(self):
        if self.ser.isOpen():
            self.ser.close()
