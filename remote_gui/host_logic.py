# host_logic.py
# This file contains the logic for the host (server) side of the application.

import socket
import threading
import time
import mss # For screen capturing
import pynput # For keyboard and mouse control
import json # For sending structured input data
from PIL import Image # Only need Image, not ImageTk here for host side
import io

# Import configuration constants from the package's config module
from .config import HOST_PORT, MAX_PACKET_SIZE, JPEG_QUALITY

def start_host_server(app_instance):
    """
    Starts the host server to listen for client connections.
    This function runs in a separate thread.

    Args:
        app_instance (RemoteGUIApp): The main application instance to access shared state and Tkinter methods.
    """
    try:
        # Create a TCP/IP socket
        app_instance.host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reusing the address immediately after closing (prevents "Address already in use" errors)
        app_instance.host_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to the IP address and port
        app_instance.host_socket.bind((app_instance.ip_address, HOST_PORT))
        # Listen for incoming connections (max 1 client at a time for this MVP)
        app_instance.host_socket.listen(1)
        
        # Update GUI status on the main thread
        app_instance.master.after(0, lambda: app_instance.host_status_label.config(text=f"Listening on {app_instance.ip_address}:{HOST_PORT}...", foreground='#2ecc71'))

        # Loop to continuously accept new connections
        while app_instance.host_socket:
            try:
                # Accept a new connection
                conn, addr = app_instance.host_socket.accept()
                with conn: # Use 'with' statement for automatic socket closing
                    app_instance.master.after(0, lambda: app_instance.host_status_label.config(text=f"Client connected from {addr[0]}! Starting screen share...", foreground='#2ecc71'))
                    app_instance.screen_sharing_active = True
                    app_instance.input_control_active = True

                    # Start threads for sending screen data and receiving input data
                    screen_send_thread = threading.Thread(target=send_screen_data, args=(app_instance, conn,), daemon=True)
                    input_receive_thread = threading.Thread(target=receive_input_data, args=(app_instance, conn,), daemon=True)

                    screen_send_thread.start()
                    input_receive_thread.start()

                    # Wait for both threads to complete (e.g., when client disconnects)
                    screen_send_thread.join()
                    input_receive_thread.join()

                    # Update GUI status after client disconnects
                    app_instance.master.after(0, lambda: app_instance.host_status_label.config(text="Client disconnected. Waiting for new connection...", foreground='#f1c40f'))
                    app_instance.screen_sharing_active = False
                    app_instance.input_control_active = False
            except socket.timeout:
                # This can happen if a timeout is set on accept, just continue listening
                pass
            except OSError as e:
                # Handle cases where the socket is intentionally closed (e.g., by stop_host_and_return_to_main)
                if "Bad file descriptor" in str(e) or "Socket is closed" in str(e):
                    print("Host socket closed, stopping listener.")
                    break # Exit loop if socket is closed intentionally
                print(f"Host accept error: {e}")
                app_instance.master.after(0, lambda: app_instance.host_status_label.config(text=f"Host error: {e}", foreground='#e74c3c'))
                break # Break on critical error
            except Exception as e:
                print(f"Host connection handling error: {e}")
                app_instance.master.after(0, lambda: app_instance.host_status_label.config(text=f"Host error: {e}", foreground='#e74c3c'))
                break # Break on critical error

    except Exception as e:
        print(f"Host server startup error: {e}")
        app_instance.master.after(0, lambda: app_instance.host_status_label.config(text=f"Host startup error: {e}", foreground='#e74c3c'))

def send_screen_data(app_instance, conn):
    """
    Continuously captures the host's screen and sends it as JPEG data to the client.
    This function runs in a separate thread.

    Args:
        app_instance (RemoteGUIApp): The main application instance.
        conn (socket.socket): The connected client socket.
    """
    sct = mss.mss() # Initialize MSS for screen capturing
    monitor = sct.monitors[0] # Capture the primary monitor (index 0)

    while app_instance.screen_sharing_active:
        try:
            # Capture screen image
            sct_img = sct.grab(monitor)
            # Convert MSS image to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)

            # Compress image to JPEG format in a byte stream
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=JPEG_QUALITY)
            img_bytes = img_byte_arr.getvalue()

            # Send the size of the image data (4 bytes, big-endian)
            conn.sendall(len(img_bytes).to_bytes(4, 'big'))
            # Send the actual image data
            conn.sendall(img_bytes)

            time.sleep(0.05) # Control frame rate (e.g., 20 FPS = 1/20 = 0.05 seconds)

        except ConnectionResetError:
            print("Client disconnected during screen send.")
            app_instance.screen_sharing_active = False
            app_instance.input_control_active = False
            break
        except Exception as e:
            print(f"Error sending screen data: {e}")
            app_instance.screen_sharing_active = False
            app_instance.input_control_active = False
            break

def receive_input_data(app_instance, conn):
    """
    Receives input commands (mouse/keyboard) from the client and simulates them on the host.
    This function runs in a separate thread.

    Args:
        app_instance (RemoteGUIApp): The main application instance.
        conn (socket.socket): The connected client socket.
    """
    mouse = pynput.mouse.Controller() # Controller for mouse actions
    keyboard = pynput.keyboard.Controller() # Controller for keyboard actions

    while app_instance.input_control_active:
        try:
            # Receive the length of the incoming input command (4 bytes)
            len_bytes = conn.recv(4)
            if not len_bytes:
                break # Connection closed by client
            input_len = int.from_bytes(len_bytes, 'big')

            # Receive the actual input command data in chunks
            input_data_bytes = b''
            while len(input_data_bytes) < input_len:
                # Receive up to MAX_PACKET_SIZE or remaining bytes
                packet = conn.recv(min(input_len - len(input_data_bytes), MAX_PACKET_SIZE))
                if not packet:
                    break # Connection closed
                input_data_bytes += packet

            if len(input_data_bytes) != input_len:
                print("Incomplete input data received.")
                continue # Skip processing if data is incomplete

            # Decode JSON command
            input_command = json.loads(input_data_bytes.decode('utf-8'))
            command_type = input_command.get('type')

            # Process different types of input commands
            if command_type == 'mouse_move':
                x, y = input_command['x'], input_command['y']
                # pynput.mouse.Controller.position sets absolute coordinates
                mouse.position = (x, y)
            elif command_type == 'mouse_click':
                x, y = input_command['x'], input_command['y']
                button_name = input_command['button']
                pressed = input_command['pressed']
                # Determine which mouse button was clicked
                button = pynput.mouse.Button.left if button_name == 'left' else pynput.mouse.Button.right
                mouse.position = (x, y) # Move mouse to position before clicking
                if pressed:
                    mouse.press(button)
                else:
                    mouse.release(button)
            elif command_type == 'key_event':
                key_char = input_command['key']
                pressed = input_command['pressed']
                try:
                    # Try to get special keys (e.g., 'enter', 'shift')
                    key = pynput.keyboard.Key[key_char]
                except KeyError:
                    # If not a special key, treat as a character
                    key = pynput.keyboard.KeyCode.from_char(key_char)

                if pressed:
                    keyboard.press(key)
                else:
                    keyboard.release(key)
            elif command_type == 'scroll':
                dx, dy = input_command['dx'], input_command['dy']
                mouse.scroll(dx, dy)

        except ConnectionResetError:
            print("Client disconnected during input receive.")
            app_instance.screen_sharing_active = False
            app_instance.input_control_active = False
            break
        except json.JSONDecodeError:
            print("Received malformed JSON input data.")
        except Exception as e:
            print(f"Error receiving/processing input data: {e}")
            app_instance.screen_sharing_active = False
            app_instance.input_control_active = False
            break

    print("Input receive thread stopped.")