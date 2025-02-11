# config.py
# Configuration settings for serial ports, baud rates, and file paths.

MOTOR_COM_PORT = 'COM3'
ACQ_COM_PORT = 'COM4'
BAUD_RATE = 9600
SERIAL_TIMEOUT = 1  # in seconds

# New: Maximum polling attempts for acquiring an "F" response.
MAX_POLL_ATTEMPTS = 500  # 100 * 100ms ≈ 10 seconds
