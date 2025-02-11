# utils/conversions.py

def text_to_hex(text: str) -> str:
    """
    Convert a text string to its hexadecimal representation.
    """
    return ''.join(format(ord(c), '02X') for c in text)

def hex_to_text(hex_str: str) -> str:
    """
    Convert a hexadecimal string back to text.
    """
    try:
        return bytes.fromhex(hex_str).decode()
    except Exception:
        return ""


def hex_to_current(hex_str: str, nFR: int = 65535, full_scale_current: float = 25.0) -> float:
    """
    Convert a hexadecimal string (from a 16-bit ADC reading) into the current in amperes
    using the continuous mode formula:

        I_c = (n_ENTREE / nFR) * full_scale_current

    :param hex_str: The ADC reading as a hexadecimal string.
    :param nFR: The full-scale ADC value (default is 65535 for 16-bit data).
    :param full_scale_current: The current corresponding to full scale (default is 25 A).
    :return: The current (in amperes).
    """
    try:
        # Convert the hex string to an integer.
        nENTREE = int(hex_str, 16)
        current = (nENTREE / nFR) * full_scale_current
        return current
    except Exception as e:
        # You may wish to log the error or handle it as needed.
        return 0.0
