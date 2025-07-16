# This is the main entry point for the application.
# Save this file as 'main.py' in the root of your project directory (e.g., 'remote_gui_app_project/main.py').

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import socket # Only for socket.SHUT_RDWR

# Import modules from the 'remote_gui' package
from remote_gui import host_logic
from remote_gui import client_logic
from remote_gui import utils
from remote_gui.config import HOST_PORT # Only need HOST_PORT here for QR data

class RemoteGUIApp:
    def __init__(self, master):
        self.master = master
        master.title("Remote GUI MVP")
        master.geometry("600x500")
        master.resizable(False, False)
        master.configure(bg="#2c3e50")

        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#34495e')
        style.configure('TLabel', background='#34495e', foreground='#ecf0f1', font=('Inter', 12))
        style.configure('TButton', background='#2ecc71', foreground='white', font=('Inter', 12, 'bold'), borderwidth=0, focusthickness=3, focuscolor='none')
        style.map('TButton', background=[('active', '#27ae60')])
        style.configure('TEntry', fieldbackground='#ecf0f1', foreground='#2c3e50', font=('Inter', 12))

        self.current_frame = None
        self.host_socket = None
        self.client_socket = None
        self.screen_sharing_active = False
        self.input_control_active = False
        self.input_listener = None # Not directly used here, but kept for consistency

        # Expose messagebox for client_logic to use
        self.messagebox = messagebox

        self.show_main_menu()

    def clear_frame(self):
        """Clears the current frame content."""
        if self.current_frame:
            self.current_frame.destroy()

    def show_main_menu(self):
        """Displays the main menu with Host/Client selection."""
        self.clear_frame()
        self.current_frame = ttk.Frame(self.master, padding="20 20 20 20")
        self.current_frame.pack(expand=True, fill="both")

        title_label = ttk.Label(self.current_frame, text="Choose Your Role", font=('Inter', 24, 'bold'), background='#34495e', foreground='#ecf0f1')
        title_label.pack(pady=40)

        host_button = ttk.Button(self.current_frame, text="Become Host", command=self.show_host_screen, width=20)
        host_button.pack(pady=15, ipadx=10, ipady=10)

        client_button = ttk.Button(self.current_frame, text="Become Client", command=self.show_client_screen, width=20)
        client_button.pack(pady=15, ipadx=10, ipady=10)

    def show_host_screen(self):
        """Displays the host screen with IP and QR code."""
        self.clear_frame()
        self.current_frame = ttk.Frame(self.master, padding="20 20 20 20")
        self.current_frame.pack(expand=True, fill="both")

        back_button = ttk.Button(self.current_frame, text="← Back", command=self.stop_host_and_return_to_main, width=10)
        back_button.pack(pady=10, anchor='nw')

        host_title = ttk.Label(self.current_frame, text="Host Mode", font=('Inter', 20, 'bold'), background='#34495e', foreground='#ecf0f1')
        host_title.pack(pady=20)

        self.ip_address = utils.get_local_ip()
        ip_label = ttk.Label(self.current_frame, text=f"Your Local IP: {self.ip_address}", font=('Inter', 14))
        ip_label.pack(pady=10)

        qr_data = f"Connect to: {self.ip_address}:{HOST_PORT}"
        self.qr_image = utils.generate_qr_code(qr_data)
        qr_canvas = tk.Canvas(self.current_frame, width=200, height=200, bg="white", highlightthickness=0)
        qr_canvas.create_image(0, 0, anchor=tk.NW, image=self.qr_image)
        qr_canvas.pack(pady=20)

        qr_info_label = ttk.Label(self.current_frame, text="Scan this QR code or use the IP address to connect.", font=('Inter', 10, 'italic'))
        qr_info_label.pack(pady=5)

        self.host_status_label = ttk.Label(self.current_frame, text="Starting host server...", font=('Inter', 12), foreground='#f1c40f')
        self.host_status_label.pack(pady=20)

        # Start host server in a thread, passing the app instance
        self.host_thread = threading.Thread(target=host_logic.start_host_server, args=(self,), daemon=True)
        self.host_thread.start()

    def stop_host_and_return_to_main(self):
        """Stops host operations and returns to main menu."""
        self.screen_sharing_active = False # Signal threads to stop
        self.input_control_active = False # Signal threads to stop
        if self.host_socket:
            try:
                self.host_socket.shutdown(socket.SHUT_RDWR)
                self.host_socket.close()
            except OSError as e:
                print(f"Error shutting down host socket: {e}")
            self.host_socket = None
        self.show_main_menu()

    def show_client_screen(self):
        """Displays the client screen for entering host IP."""
        self.clear_frame()
        self.current_frame = ttk.Frame(self.master, padding="20 20 20 20")
        self.current_frame.pack(expand=True, fill="both")

        back_button = ttk.Button(self.current_frame, text="← Back", command=self.stop_client_and_return_to_main, width=10)
        back_button.pack(pady=10, anchor='nw')

        client_title = ttk.Label(self.current_frame, text="Client Mode", font=('Inter', 20, 'bold'), background='#34495e', foreground='#ecf0f1')
        client_title.pack(pady=20)

        ip_entry_label = ttk.Label(self.current_frame, text="Enter Host IP Address:", font=('Inter', 14))
        ip_entry_label.pack(pady=10)

        self.host_ip_entry = ttk.Entry(self.current_frame, width=30)
        self.host_ip_entry.pack(pady=5)
        self.host_ip_entry.insert(0, "127.0.0.1") # Default for testing

        connect_button = ttk.Button(self.current_frame, text="Connect to Host", command=self._initiate_client_connection, width=20)
        connect_button.pack(pady=20, ipadx=10, ipady=10)

        self.client_status_label = ttk.Label(self.current_frame, text="Enter host IP and click Connect.", font=('Inter', 12), foreground='#ecf0f1')
        self.client_status_label.pack(pady=20)

        self.remote_screen_label = ttk.Label(self.current_frame, text="Remote Screen will appear here...", background='black', foreground='white')
        self.remote_screen_label.pack(expand=True, fill="both", pady=10)
        # Bind client input events to functions in client_logic, passing 'self' (the app instance)
        self.remote_screen_label.bind("<Motion>", lambda event: client_logic.on_mouse_move(self, event))
        self.remote_screen_label.bind("<ButtonPress-1>", lambda event: client_logic.on_mouse_click(self, event, 'left', True))
        self.remote_screen_label.bind("<ButtonRelease-1>", lambda event: client_logic.on_mouse_click(self, event, 'left', False))
        self.remote_screen_label.bind("<ButtonPress-3>", lambda event: client_logic.on_mouse_click(self, event, 'right', True))
        self.remote_screen_label.bind("<ButtonRelease-3>", lambda event: client_logic.on_mouse_click(self, event, 'right', False))
        self.remote_screen_label.bind("<MouseWheel>", lambda event: client_logic.on_mouse_scroll(self, event)) # For Windows/macOS
        self.remote_screen_label.bind("<Button-4>", lambda event: client_logic.on_mouse_scroll(self, event, 'up')) # For Linux scroll up
        self.remote_screen_label.bind("<Button-5>", lambda event: client_logic.on_mouse_scroll(self, event, 'down')) # For Linux scroll down

        # Make the remote screen label focusable to capture keyboard events
        self.remote_screen_label.focus_set()
        self.remote_screen_label.bind("<KeyPress>", lambda event: client_logic.on_key_press(self, event))
        self.remote_screen_label.bind("<KeyRelease>", lambda event: client_logic.on_key_release(self, event))

        self.remote_image_tk = None # To keep a reference to the image

    def _initiate_client_connection(self):
        """Wrapper to call client_logic's start_client_connection."""
        host_ip = self.host_ip_entry.get()
        client_logic.start_client_connection(self, host_ip)

    def stop_client_and_return_to_main(self):
        """Stops client operations and returns to main menu."""
        self.screen_sharing_active = False # Signal threads to stop
        self.input_control_active = False # Signal threads to stop
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError as e:
                print(f"Error shutting down client socket: {e}")
            self.client_socket = None
        if self.input_listener:
            self.input_listener.stop()
            self.input_listener = None
        self.show_main_menu()

if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteGUIApp(root)
    root.mainloop()
