from PyQt5.QtCore import pyqtSignal, QObject
import serial

class SerialCommunication(QObject):
    ACK_SIGNAL = pyqtSignal(str)
    NAK_SIGNAL = pyqtSignal(str)

    COM_PORT = 'COM3'
    BAUD_RATE = 9600
    TIMEOUT = 1

    def __init__(self):
        super().__init__()

        # Initialize the serial port
        self.ser = serial.Serial(self.COM_PORT, self.BAUD_RATE, timeout=self.TIMEOUT)

    def send_command(self, text_command):
        try:
            # Convert text_command to hexadecimal representation
            hex_command = ''.join(format(ord(char), '02X') for char in text_command)

            # Construct the full command with start (STX), controller address, hex command, and end (ETX)
            full_command = f"02 30 {hex_command} 03"

            # Convert the full command to bytes and send it over the serial port
            command_bytes = bytes.fromhex(''.join(full_command.split()))
            self.ser.write(command_bytes)

            print(f"Command '{full_command}' sent to {self.COM_PORT} successfully.")

            # Read the response from the serial port and format it for easier interpretation
            response = self.ser.readline().strip()
            response_repr = repr(response)[2:-1].replace('\\x02', '<STX>').replace('\\x06', '<ACK>') \
                .replace('\\x03', '<ETX>').replace('\\x15', '<NAK>')

            # Emit signals based on the type of response received
            if '<ACK>' in response_repr:
                self.ACK_SIGNAL.emit(response_repr)
            elif '<NAK>' in response_repr:
                self.NAK_SIGNAL.emit(response_repr)
        except serial.SerialException as e:
            print(f"Error: {e}")

    def close_serial_port(self):
        if self.ser.isOpen():
            self.ser.close()
