# 🛠️ CNC Controller Application

A modern, modular desktop application for controlling CNC machines via serial communication. It features a rich PySide6-based GUI, robust backend for multi-firmware support, real-time status, and advanced command routing. Designed for both end-users and developers.

---

## 📦 Features

- **Multi-firmware support**: GRBL, Marlin, Repetier, Smoothieware, Klipper, and custom (Invariance)
- **Serial connection management**: Auto-detection, auto-reconnect, connection statistics, error handling
- **G-code execution**: Jog controls, home/park/start/emergency stop, command queueing with priorities
- **Actuator & axis configuration**: UI for editing, saving, and previewing actuator and axis settings
- **Unified logging**: All actions and errors logged in a central panel
- **Persistent settings**: Automatic save/restore of all configs and UI state
- **Dark theme**: Modern, customizable UI with global and component styles
- **Extensible architecture**: Modular backend and UI, easy to add new features

---

## 🏗️ Architecture Overview

```
main.py                # Application entry point
assets/style.qss       # Global dark theme stylesheet
core/                  # Core backend modules
  config_manager.py    # Config management (JSON, QSettings)
  firmware_utils.py    # Firmware detection/utilities
  gcode_executor.py    # G-code execution engine
  jog_controller.py    # Jog movement logic
  serial_manager.py    # Serial communication
ui/                    # User interface
  main_window.py       # Main window, central hub
  log_panel.py         # Log display
  jog_panel.py         # Jog controls
  components/          # Reusable UI widgets
  tab_config.py        # Axis config tab
  tab_actuators.py     # Actuators tab
  tab_connection.py    # Serial connection tab
  tab_console.py       # Console tab
```

### 🖥️ MainWindow Signal Flow

- **LogPanel**: Shows all logs and errors
- **JogPanel**: Jog, home, park, start, emergency stop
- **ConfigTab**: Axis configuration
- **ActuatorsTab**: Actuator configuration and testing
- **ConnectionTab**: Serial port management, firmware detection
- **ConsoleTab**: Send raw commands, view responses

All commands and status updates are routed through the MainWindow for centralized control and logging.

---

## 🚀 Getting Started

### 1. **Install dependencies**

- Python 3.8+
- [PySide6](https://pypi.org/project/PySide6/)

```
pip install -r requirements.txt
```

### 2. **Run the application**

```
python main.py
```

### 3. **Connect your CNC controller**
- Go to the **Connection** tab
- Select your serial port and click **Connect**
- Firmware is auto-detected; status is shown in the UI

### 4. **Configure axes and actuators**
- Use the **Configuration** and **Actuators** tabs to set up your machine
- All changes are saved automatically

### 5. **Send commands and jog**
- Use the **Jog** panel for movement
- Use the **Console** tab for raw G-code or firmware commands

---

## 🧩 File & Data Structure

- `data/config.json` — Main configuration (axes, actuators, UI, etc.)
- `data/log.txt` — Application logs
- `data/micros.json` — Macro commands
- `assets/style.qss` — Global stylesheet

---

## 🧪 Testing

- **SerialManager**: `python test_serial_manager.py`
- **Hardware connection**: `python test_hardware_connection.py`
- **Full app integration**: `python main.py`

See `SERIAL_MANAGER_TESTING.md` and `SERIAL_MANAGER_INTEGRATION.md` for detailed test cases and troubleshooting.

---

## ⚙️ Advanced Features

- **Command queue with priorities**
- **Thread-safe serial communication**
- **Auto-reconnect with exponential backoff**
- **Firmware-specific command sets and parsing**
- **Real-time status propagation to all UI components**
- **Comprehensive error handling and recovery**
- **Performance and connection statistics**

---

## 🗺️ Roadmap / TODO

- File upload/download (G-code)
- Real-time position tracking
- Advanced G-code parsing
- Multi-controller/network support
- Plugin system

---

## 📝 Contributing

Contributions are welcome! Please open issues or pull requests for bug fixes, features, or documentation improvements.

---

## 📄 License

MIT License (see LICENSE file)

---

## 🙏 Acknowledgements

- [PySide6](https://wiki.qt.io/Qt_for_Python)
- Open-source CNC firmware projects: GRBL, Marlin, Repetier, Smoothieware, Klipper

---

*For wiring diagrams, signal flow, and detailed integration, see `WIRING_DIAGRAM.md`.* 