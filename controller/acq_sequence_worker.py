import csv
import time

from PyQt5.QtCore import QObject, pyqtSignal

from config import CSV_OUTPUT_PATH


class AcqSequenceWorker(QObject):
    """
    Worker that runs the acquisition sequence on a background thread.

    For each motor (first X, then Y), the sequence is:
      1. Send the motor’s "0+" command (e.g. "X0+" or "Y0+").
      2. Wait 10 seconds.
      3. Send "A" to the acquisition card.
      4. Send the motor’s drive command (e.g. "X-400" or "Y-400").
      5. Continuously send "A" to the acquisition card until a response "F" is received.
      6. Once "F" is received, send "D" to the acquisition card.
      7. Read and collect data until the termination string "00000000,00000000" is received.
      8. Save the collected data to a CSV file (one file per motor).
      9. Then repeat the process for the next motor.
    """
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, motor_model, acq_model, parent=None):
        super().__init__(parent)
        self.motor_model = motor_model
        self.acq_model = acq_model
        self._running = True

    def run(self):
        try:
            # Define motor profiles for the two motors.
            motor_profiles = [
                {"label": "X", "initial": "X0+", "drive": "X-400", "csv": "acquired_data_X.csv"},
                {"label": "Y", "initial": "Y0+", "drive": "Y-400", "csv": "acquired_data_Y.csv"}
            ]
            # Continue looping until stopped.
            while self._running:
                for profile in motor_profiles:
                    if not self._running:
                        break

                    motor_label = profile["label"]
                    initial_cmd = profile["initial"]
                    drive_cmd = profile["drive"]
                    csv_filename = profile["csv"]

                    print(f"[AcqSequenceWorker] Starting sequence for {motor_label} motor.")

                    # Step 1: Send the initial command to the motor.
                    self.motor_model.send_command(initial_cmd)
                    time.sleep(5)  # Wait 10 seconds

                    # Step 2: Send "A" to the acquisition card.
                    self.acq_model.send_serial_data("A")

                    # Step 3: Send the drive command to the motor.
                    self.motor_model.send_command(drive_cmd)

                    # Step 4: Poll the acquisition card by sending "A" repeatedly until a response "F" is received.
                    response = None
                    while self._running:
                        self.acq_model.send_serial_data("A")
                        time.sleep(0.1)  # Allow time for the response
                        response = self.acq_model.read_serial_data()
                        print(f"[AcqSequenceWorker] Polling ({motor_label}): sent 'A', received '{response}'")
                        if response == "F":
                            break

                    if not self._running:
                        break

                    # Step 5: Once "F" is received, send the "D" command.
                    self.acq_model.send_serial_data("D")
                    print(f"[AcqSequenceWorker] Sent 'D' command after receiving 'F' for {motor_label} motor.")

                    # Step 6: Read and collect data until termination string is received.
                    collected_data = []
                    while self._running:
                        data_line = self.acq_model.read_serial_data()
                        print(f"[AcqSequenceWorker] Data line ({motor_label}): {data_line}")
                        if data_line == "00000000,00000000":
                            break
                        collected_data.append(data_line)

                    # Step 7: Save the collected data to a CSV file.
                    with open(csv_filename, 'w', newline='') as csv_file:
                        writer = csv.writer(csv_file)
                        for item in collected_data:
                            writer.writerow([item])
                    print(f"[AcqSequenceWorker] Data saved to {csv_filename} for {motor_label} motor.")

                    # Optional pause between motor cycles.
                    time.sleep(1)
        except Exception as e:
            self.errorOccurred.emit(str(e))
        finally:
            self.finished.emit()

    def stop(self):
        self._running = False