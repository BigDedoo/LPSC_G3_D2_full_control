"""
This module implements a ProgramUploader class that reads a .txt file,
removes any line numbers, and sends the file’s content to the motor controller
using the following protocol (now using the motor_model.send_command method):

  1. Header frame:
       <STX>controller_address + "QP" + program_name + " S" + byte_count + <ETX>
     Controller response (after conversion by send_command):
       "<STX><ACK>O<ETX>"  – if the program does not exist and RAM is sufficient
       "<STX><ACK>E<ETX>"  – if the program exists (overwrite required)

  2. Program transmission:
       - Block 1: program name + ETB + first (256 - (len(program_name)+1)) characters
         of data (if needed, padded with EOT to 256 characters).
       - Subsequent blocks: Each 256-character block (padded with EOT as needed).
       - Each block is sent by calling send_command with the payload.
       - After each block, the controller is expected to respond with:
             "<STX><ACK><ETX>"

Note:
  In this rewritten uploader we treat all data as text (assuming ASCII) so that
  the motor_model.send_command (which performs a conversion to hex internally)
  produces the expected framing.
"""

import re
import time
import logging
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ProgramUploader(QObject):
    finished = pyqtSignal()
    errorOccurred = pyqtSignal(str)
    progressUpdated = pyqtSignal(str)  # For updating UI progress messages

    def __init__(self, motor_model, file_path, program_name, parent=None):
        """
        :param motor_model: Instance of MotorModel to use for serial I/O.
                            Now, this uploader uses motor_model.send_command.
        :param file_path: Path to the .txt file to be uploaded.
        :param program_name: The program name (maximum 8 characters). It will not be padded
                             with blanks if shorter than 8 characters.
        """
        super().__init__(parent)
        self.motor_model = motor_model
        self.file_path = file_path
        # Keep only up to 8 characters without padding.
        self.program_name = program_name.strip()[:8]
        self._running = True

        # Define control characters as strings (using their ASCII characters).
        self.STX = chr(0x02)
        self.ETX = chr(0x03)
        self.EOT = chr(0x04)
        self.ETB = chr(0x17)
        self.ACK = chr(0x06)

        # The motor model already uses controller address 0x30 (which is the character '0').
        self.CONTROLLER_ADDRESS = '0'

    def remove_line_numbers(self, text):
        """
        Remove any leading line numbers from each line.
        Assumes the line number is at the beginning of the line followed by whitespace.
        """
        lines = text.splitlines()
        cleaned_lines = [re.sub(r'^\d+\s*', '', line) for line in lines]
        return "\n".join(cleaned_lines)

    def read_file_content(self):
        """
        Read the file, remove line numbers, and return the content as an ASCII string.
        """
        try:
            with open(self.file_path, 'r', encoding='ascii') as f:
                content = f.read()
            content = self.remove_line_numbers(content)
            return content
        except Exception as e:
            raise Exception(f"Error reading file: {e}")

    def upload(self):
        """Main method that performs the program upload using motor_model.send_command."""
        try:
            # === Step 1. Read file and build header payload ===
            file_text = self.read_file_content()
            total_chars = len(file_text)  # For ASCII, character count equals byte count.
            self.progressUpdated.emit(f"File read: {total_chars} bytes.")

            # Build header payload: "QP" + program_name + " S" + byte_count (in ascii)
            header_payload = "QP" + self.program_name + " S" + str(total_chars)
            self.progressUpdated.emit("Sending header frame...")
            header_resp = self.motor_model.send_command(header_payload)
            # For send_command, control characters are replaced by markers, so we expect:
            # "<STX><ACK>O<ETX>" or "<STX><ACK>E<ETX>"
            if not (header_resp.startswith("<STX><ACK>") and header_resp.endswith("<ETX>")):
                raise Exception(f"Invalid header response: {header_resp}")
            # Extract the response code (the character between <ACK> and <ETX>).
            response_code = header_resp[len("<STX><ACK>"):-len("<ETX>")]
            if response_code not in ["O", "E"]:
                raise Exception(f"Unexpected header response code: {response_code}")
            self.progressUpdated.emit(f"Controller response: {response_code}")

            # === Step 2. Prepare the program blocks ===
            # The protocol for Block 1:
            #   Block 1 payload: program name + ETB + first (256 - (len(program_name)+1)) characters of data.
            header_block_size = len(self.program_name) + 1  # program name + ETB
            first_chunk_size = 256 - header_block_size

            blocks = []
            if total_chars <= first_chunk_size:
                # Entire file fits in Block 1; no padding with EOT is needed.
                block1 = self.program_name + self.ETB + file_text
                blocks.append(block1)
            else:
                first_chunk = file_text[:first_chunk_size]
                block1 = self.program_name + self.ETB + first_chunk
                # Pad block1 to 256 characters if needed.
                if len(block1) < 256:
                    block1 = block1.ljust(256, self.EOT)
                blocks.append(block1)

                remaining_text = file_text[first_chunk_size:]
                # Build subsequent 256-character blocks.
                for i in range(0, len(remaining_text), 256):
                    block = remaining_text[i:i + 256]
                    if len(block) < 256:
                        block = block.ljust(256, self.EOT)
                    blocks.append(block)

            # === Step 3. Transmit each block ===
            block_number = 1
            expected_block_response = "<STX><ACK><ETX>"
            for block in blocks:
                print(block)
                self.progressUpdated.emit(f"Sending block {block_number}...")
                # Send the block payload (the motor_model.send_command method will wrap it).
                block_resp = self.motor_model.send_command(block)
                if block_resp != expected_block_response:
                    raise Exception(f"Invalid response for block {block_number}: {block_resp}")
                self.progressUpdated.emit(f"Block {block_number} transmitted successfully.")
                block_number += 1

            self.progressUpdated.emit("Program upload completed successfully.")
            self.finished.emit()

        except Exception as e:
            error_msg = f"Program upload error: {e}"
            logger.error(error_msg)
            self.errorOccurred.emit(error_msg)
            self.finished.emit()
