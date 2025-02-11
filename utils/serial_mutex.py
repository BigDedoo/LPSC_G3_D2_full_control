# serial_mutex.py
from PyQt5.QtCore import QMutex

# Create separate recursive mutexes for each serial port.
motor_mutex = QMutex(QMutex.Recursive)  # For motor communications (COM3)
acq_mutex = QMutex(QMutex.Recursive)    # For acquisition communications (COM4)
