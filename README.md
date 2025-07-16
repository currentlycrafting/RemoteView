# Remote GUI MVP (Minimal Viable Product)

A simple proof-of-concept Python application for remote desktop control, allowing a user to act as either a **host** (sharing their screen and receiving input) or a **client** (viewing the host's screen and sending input).

> ⚠️ **Disclaimer**: This MVP is built for demonstration purposes and does **not** include any security features (encryption, authentication). **Do not** use it for sensitive operations or over untrusted networks. Performance may vary depending on network conditions and system resources.

---

## 🚀 Features

- **Role Selection**: Choose to be a Host or a Client upon launching the application.

### 🖥 Host Mode

- Displays the host's local IP address and a QR code for easy client connection.
- Captures the host's primary screen in real-time.
- Receives mouse and keyboard input from the client and simulates it on the host's desktop.

### 🖱 Client Mode

- Allows entering a host's IP address to connect.
- Displays the remote host's screen.
- Sends local mouse movements, clicks, scrolls, and keyboard presses to the host.

- **Cross-Platform (Python)**: Designed to run on operating systems where Python, Tkinter, mss, and pynput are supported (Windows, macOS, Linux).
- **Bundled Executable**: Can be packaged into a standalone executable using PyInstaller.

---

## 🛠 Technologies Used

- **Python 3.x** – Core programming language
- **Tkinter** – Graphical user interface
- **mss** – High-performance screen capture
- **pynput** – Keyboard and mouse control
- **qrcode** – QR code generation
- **Pillow (PIL Fork)** – Image manipulation (resizing, format conversion)
- **socket module** – TCP communication
- **json module** – Serialization of input events
- **PyInstaller** – Bundling into an executable

---

## 📁 Project Structure

remote_gui_app_project/
├── main.py # Main application entry point and GUI setup
├── requirements.txt # List of Python dependencies
├── remote_app_icon.icns # Application icon for macOS (static)
└── remote_gui/
  ├── init.py # Package initializer
  ├── config.py # Configuration constants (ports, quality)
  ├── utils.py # Utility functions (get IP, generate QR code)
  ├── host_logic.py # Core logic for the host
  └── client_logic.py # Core logic for the client



---

## ⚙️ Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/RemoteView.git
cd RemoteView

