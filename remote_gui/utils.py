# utils.py
# This file contains utility functions used across the application.

import socket
import qrcode
from PIL import Image, ImageTk
import io

def get_local_ip():
    """
    Attempts to get the local IP address of the machine.
    It connects to a public DNS server (8.8.8.8) to determine
    the IP address used for outbound connections, then closes the socket.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # Connect to a public DNS server
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error getting IP: {e}")
        return "127.0.0.1 (Error getting IP)" # Fallback to loopback if error occurs

def generate_qr_code(data, size=(200, 200)):
    """
    Generates a QR code image from the given data string.

    Args:
        data (str): The string data to encode in the QR code (e.g., IP address).
        size (tuple): A tuple (width, height) for the desired image size.

    Returns:
        PIL.ImageTk.PhotoImage: A Tkinter-compatible PhotoImage object of the QR code.
    """
    qr = qrcode.QRCode(
        version=1, # Controls the size of the QR code. 1 is the smallest.
        error_correction=qrcode.constants.ERROR_CORRECT_L, # Error correction level. L = Low.
        box_size=10, # How many pixels each "box" of the QR code is.
        border=4, # How many boxes thick the border should be.
    )
    qr.add_data(data)
    qr.make(fit=True) # Adjusts the version to fit the data.
    
    # Create a PIL Image from the QR code and convert to RGB.
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Resize the image to the specified size using LANCZOS for high-quality downsampling.
    img = img.resize(size, Image.Resampling.LANCZOS)
    
    # Convert the PIL Image to a Tkinter PhotoImage.
    return ImageTk.PhotoImage(img)
