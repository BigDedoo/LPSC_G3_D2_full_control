# utils/protocol_formatter.py

from utils.conversions import text_to_hex


class ProtocolFormatter:
    @staticmethod
    def format_motor_command(text_command: str) -> bytes:
        """
        Formats a motor command by converting the text to hexadecimal and wrapping it
        with the protocol markers:
            - STX (0x02)
            - Controller address (assumed to be '30')
            - ETX (0x03)
        """
        hex_command = text_to_hex(text_command)
        full_command = f"02 30 {hex_command} 03"
        hex_string = full_command.replace(" ", "")
        return bytes.fromhex(hex_string)

    @staticmethod
    def format_acq_command(text_command: str) -> bytes:
        """
        Formats an acquisition command by converting the text to hexadecimal and appending
        the carriage return (0x0D).
        """
        hex_command = text_to_hex(text_command)
        full_command = f"{hex_command}0D"
        return bytes.fromhex(full_command)

    @staticmethod
    def parse_motor_response(response: str) -> str:
        """
        Parses the motor response by replacing control characters with readable markers.
        """
        return (response
                .replace('\x02', '<STX>')
                .replace('\x06', '<ACK>')
                .replace('\x03', '<ETX>')
                .replace('\x15', '<NAK>'))
