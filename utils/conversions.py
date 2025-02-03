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
