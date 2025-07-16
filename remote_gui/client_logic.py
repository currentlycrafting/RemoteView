# client_logic.py
# This file contains the logic for the client side of the application.

import socket
import threading
import time
import json
from PIL import Image, ImageTk # Need both Image and ImageTk for client side
import io
import tkinter as tk # For Tkinter specific constants like NW (though not directly used in this file, helpful for context)

# Import configuration constants from the package's config module
from .config import HOST_PORT, MAX_PACKET_SIZE

def start_client_connection(app_instance, host_ip):
    """
    Initiates the client connection to the host and starts screen/input threads.

    Args:
        app_instance (RemoteGUIApp): The main application instance to access shared state and Tkinter methods.
        host_ip (str): The IP address of the host to connect to.
    """
    if not host_ip:
        # Use app_instance.messagebox to show error on the main thread
        app_instance.master.after(0, lambda: app_instance.messagebox.showerror("Input Error", "Please enter a host IP address."))
        return

    app_instance.client_status_label.config(text=f"Attempting to connect to {host_ip}:{HOST_PORT}...", foreground='#f1c40f')

    try:
        app_instance.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        app_instance.client_socket.settimeout(10) # Set a timeout for connection attempt
        app_instance.client_socket.connect((host_ip, HOST_PORT))
        app_instance.client_status_label.config(text=f"Successfully connected to {host_ip}! Receiving screen...", foreground='#2ecc71')

        app_instance.screen_sharing_active = True
        app_instance.input_control_active = True

        # Start threads for receiving screen data and sending input data
        screen_receive_thread = threading.Thread(target=receive_screen_data, args=(app_instance, app_instance.client_socket,), daemon=True)
        input_send_thread = threading.Thread(target=send_input_data, args=(app_instance, app_instance.client_socket,), daemon=True)

        screen_receive_thread.start()
        input_send_thread.start()

    except socket.timeout:
        app_instance.master.after(0, lambda: app_instance.client_status_label.config(text=f"Connection to {host_ip} timed out.", foreground='#e74c3c'))
        app_instance.master.after(0, lambda: app_instance.messagebox.showerror("Connection Error", f"Could not connect to {host_ip}: Connection timed out."))
        app_instance.master.after(0, app_instance.stop_client_and_return_to_main) # Return to main menu on failure
    except ConnectionRefusedError:
        app_instance.master.after(0, lambda: app_instance.client_status_label.config(text=f"Connection to {host_ip} refused.", foreground='#e74c3c'))
        app_instance.master.after(0, lambda: app_instance.messagebox.showerror("Connection Error", f"Connection to {host_ip} refused. Is the host running and firewall configured?"))
        app_instance.master.after(0, app_instance.stop_client_and_return_to_main)
    except Exception as e:
        app_instance.master.after(0, lambda: app_instance.client_status_label.config(text=f"Client error: {e}", foreground='#e74c3c'))
        app_instance.master.after(0, lambda: app_instance.messagebox.showerror("Connection Error", f"An error occurred: {e}"))
        app_instance.master.after(0, app_instance.stop_client_and_return_to_main)

def receive_screen_data(app_instance, conn):
    """
    Continuously receives screen data (JPEG images) from the host and displays it on the client GUI.
    This function runs in a separate thread.

    Args:
        app_instance (RemoteGUIApp): The main application instance.
        conn (socket.socket): The connected host socket.
    """
    while app_instance.screen_sharing_active:
        try:
            # Receive image size first (4 bytes, big-endian)
            len_bytes = conn.recv(4)
            if not len_bytes:
                break # Connection closed by host
            img_len = int.from_bytes(len_bytes, 'big')

            # Receive the actual image data in chunks
            img_data = b''
            while len(img_data) < img_len:
                packet = conn.recv(min(img_len - len(img_data), MAX_PACKET_SIZE))
                if not packet:
                    break # Connection closed
                img_data += packet

            if len(img_data) != img_len:
                print("Incomplete image data received.")
                continue # Skip processing if data is incomplete

            # Convert received bytes to PIL Image
            img = Image.open(io.BytesIO(img_data))

            # Get the current size of the Tkinter label where the image will be displayed
            label_width = app_instance.remote_screen_label.winfo_width()
            label_height = app_instance.remote_screen_label.winfo_height()

            # Provide a reasonable default size if the label hasn't been fully rendered yet
            if label_width == 1 or label_height == 1:
                label_width = 800
                label_height = 600

            img_width, img_height = img.size
            aspect_ratio = img_width / img_height

            # Resize image to fit the label while maintaining aspect ratio
            if img_width > label_width or img_height > label_height:
                if (label_width / aspect_ratio) <= label_height:
                    new_width = label_width
                    new_height = int(label_width / aspect_ratio)
                else:
                    new_height = label_height
                    new_width = int(label_height * aspect_ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert PIL Image to Tkinter PhotoImage and update the label on the main thread
            app_instance.remote_image_tk = ImageTk.PhotoImage(img)
            app_instance.master.after(0, lambda: app_instance.remote_screen_label.config(image=app_instance.remote_image_tk))

        except ConnectionResetError:
            print("Host disconnected during screen receive.")
            app_instance.master.after(0, lambda: app_instance.client_status_label.config(text="Host disconnected.", foreground='#e74c3c'))
            app_instance.screen_sharing_active = False
            app_instance.input_control_active = False
            break
        except Exception as e:
            print(f"Error receiving/displaying screen data: {e}")
            app_instance.master.after(0, lambda: app_instance.client_status_label.config(text=f"Screen error: {e}", foreground='#e74c3c'))
            app_instance.screen_sharing_active = False
            app_instance.input_control_active = False
            break
    print("Screen receive thread stopped.")
    # Automatically return to main menu if screen sharing stops (e.g., host disconnects)
    app_instance.master.after(0, app_instance.stop_client_and_return_to_main)

def send_input_data(app_instance, conn):
    """
    This thread primarily keeps the connection alive for input.
    Actual input events are captured by Tkinter binds and sent directly via `_send_input_command`.

    Args:
        app_instance (RemoteGUIApp): The main application instance.
        conn (socket.socket): The connected host socket.
    """
    while app_instance.input_control_active:
        time.sleep(0.1) # Keep thread alive, but actual sends are event-driven

    print("Input send thread stopped.")

def get_scaled_coords(app_instance, event):
    """
    Scales client mouse coordinates relative to the displayed remote screen image.
    This is a simplification. For accurate scaling, the client would need
    to know the host's actual screen resolution.

    Args:
        app_instance (RemoteGUIApp): The main application instance.
        event (tk.Event): The Tkinter mouse event object.

    Returns:
        tuple: A tuple (x, y) representing the scaled coordinates.
    """
    if not app_instance.remote_image_tk:
        return event.x, event.y

    # Get the dimensions of the currently displayed image
    displayed_img_width = app_instance.remote_image_tk.width()
    displayed_img_height = app_instance.remote_image_tk.height()

    if displayed_img_width == 0 or displayed_img_height == 0:
        return event.x, event.y # Avoid division by zero

    # Get the actual size of the Tkinter label
    label_width = app_instance.remote_screen_label.winfo_width()
    label_height = app_instance.remote_screen_label.winfo_height()

    # Calculate the offset if the image is centered within the label
    offset_x = (label_width - displayed_img_width) / 2
    offset_y = (label_height - displayed_img_height) / 2

    # Convert event coordinates relative to the displayed image's top-left corner
    relative_x = event.x - offset_x
    relative_y = event.y - offset_y

    # For this MVP, we send coordinates relative to the displayed image.
    # The host will interpret these as absolute coordinates on its screen.
    # This works best if client's remote screen label matches host's actual screen size,
    # or if the host's screen is the primary target for absolute mouse positions.
    return int(relative_x), int(relative_y)


def send_input_command(app_instance, command_type, **kwargs):
    """
    Sends an input command (mouse or keyboard event) to the host.

    Args:
        app_instance (RemoteGUIApp): The main application instance.
        command_type (str): The type of command (e.g., 'mouse_move', 'key_event').
        **kwargs: Additional data for the command (e.g., x, y, key, pressed).
    """
    if not app_instance.input_control_active or not app_instance.client_socket:
        return

    command = {'type': command_type}
    command.update(kwargs)
    command_json = json.dumps(command).encode('utf-8')

    try:
        # Send the length of the JSON command first (4 bytes)
        app_instance.client_socket.sendall(len(command_json).to_bytes(4, 'big'))
        # Send the actual JSON command data
        app_instance.client_socket.sendall(command_json)
    except ConnectionResetError:
        print("Host disconnected during input send.")
        app_instance.master.after(0, lambda: app_instance.client_status_label.config(text="Host disconnected.", foreground='#e74c3c'))
        app_instance.screen_sharing_active = False
        app_instance.input_control_active = False
        app_instance.master.after(0, app_instance.stop_client_and_return_to_main)
    except Exception as e:
        print(f"Error sending input command: {e}")

# --- Client Input Event Handlers ---
# These functions are called by Tkinter event bindings on the remote_screen_label.
# They prepare the input data and call send_input_command.

def on_mouse_move(app_instance, event):
    """Handles mouse motion events on the client's remote screen label."""
    x, y = get_scaled_coords(app_instance, event)
    send_input_command(app_instance, 'mouse_move', x=x, y=y)

def on_mouse_click(app_instance, event, button, pressed):
    """Handles mouse click (press/release) events on the client's remote screen label."""
    x, y = get_scaled_coords(app_instance, event)
    send_input_command(app_instance, 'mouse_click', x=x, y=y, button=button, pressed=pressed)

def on_mouse_scroll(app_instance, event, direction=None):
    """Handles mouse scroll events on the client's remote screen label."""
    dx, dy = 0, 0
    if event.num == 4: # Linux scroll up
        dy = 1
    elif event.num == 5: # Linux scroll down
        dy = -1
    elif event.delta: # Windows/macOS scroll (typically 120 per scroll unit)
        dy = event.delta / 120 # Normalize delta to typical scroll units

    send_input_command(app_instance, 'scroll', dx=dx, dy=dy)

def on_key_press(app_instance, event):
    """Handles keyboard key press events when the client's remote screen label has focus."""
    try:
        key_name = event.keysym # Tkinter key symbol
        # Map common Tkinter keysyms to pynput Key enum names for consistency
        if key_name == 'Return': key_name = 'enter'
        elif key_name == 'Escape': key_name = 'esc'
        elif key_name == 'Prior': key_name = 'page_up'
        elif key_name == 'Next': key_name = 'page_down'
        elif key_name == 'Up': key_name = 'up'
        elif key_name == 'Down': key_name = 'down'
        elif key_name == 'Left': key_name = 'left'
        elif key_name == 'Right': key_name = 'right'
        elif key_name == 'Control_L': key_name = 'ctrl_l'
        elif key_name == 'Control_R': key_name = 'ctrl_r'
        elif key_name == 'Alt_L': key_name = 'alt_l'
        elif key_name == 'Alt_R': key_name = 'alt_r'
        elif key_name == 'Shift_L': key_name = 'shift_l'
        elif key_name == 'Shift_R': key_name = 'shift_r'
        elif key_name == 'BackSpace': key_name = 'backspace'
        elif key_name == 'Delete': key_name = 'delete'
        elif key_name == 'Tab': key_name = 'tab'
        elif key_name == 'space': key_name = 'space' # pynput uses 'space' for spacebar
        elif key_name == 'Caps_Lock': key_name = 'caps_lock'

        send_input_command(app_instance, 'key_event', key=key_name, pressed=True)
    except Exception as e:
        print(f"Error handling key press: {e}")

def on_key_release(app_instance, event):
    """Handles keyboard key release events when the client's remote screen label has focus."""
    try:
        key_name = event.keysym
        # Map common Tkinter keysyms to pynput Key enum names
        if key_name == 'Return': key_name = 'enter'
        elif key_name == 'Escape': key_name = 'esc'
        elif key_name == 'Prior': key_name = 'page_up'
        elif key_name == 'Next': key_name = 'page_down'
        elif key_name == 'Up': key_name = 'up'
        elif key_name == 'Down': key_name = 'down'
        elif key_name == 'Left': key_name = 'left'
        elif key_name == 'Right': key_name = 'right'
        elif key_name == 'Control_L': key_name = 'ctrl_l'
        elif key_name == 'Control_R': key_name = 'ctrl_r'
        elif key_name == 'Alt_L': key_name = 'alt_l'
        elif key_name == 'Alt_R': key_name = 'alt_r'
        elif key_name == 'Shift_L': key_name = 'shift_l'
        elif key_name == 'Shift_R': key_name = 'shift_r'
        elif key_name == 'BackSpace': key_name = 'backspace'
        elif key_name == 'Delete': key_name = 'delete'
        elif key_name == 'Tab': key_name = 'tab'
        elif key_name == 'space': key_name = 'space'
        elif key_name == 'Caps_Lock': key_name = 'caps_lock'

        send_input_command(app_instance, 'key_event', key=key_name, pressed=False)
    except Exception as e:
        print(f"Error handling key release: {e}")
