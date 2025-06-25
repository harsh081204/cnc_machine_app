# ui/tab_controller.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, 
    QMessageBox, QProgressBar, QTextEdit, QGroupBox, QCheckBox, QSpinBox,
    QLineEdit, QFrame, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, Slot
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
from core.serial_manager import SerialManager, ConnectionState, FirmwareType, SerialResponse
from core.firmware_utils import FirmwareUtils
from core.config_manager import ConnectionConfig
import time


class ConnectionTab(QWidget):
    connection_status_changed = Signal(bool)  # Signal for main app to know connection status
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.firmware_utils = FirmwareUtils()
        # Replace simple thread with advanced SerialManager
        self.serial_manager = SerialManager(auto_reconnect=True, command_timeout=5.0)
        self.is_connected = False
        self.connection_timer = QTimer()
        self.port_refresh_timer = QTimer()
        self.init_ui()
        self.setup_timers()
        self.setup_serial_manager_connections()
        self.apply_styles()
        self.load_connection_config()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # Title with icon
        title_layout = QHBoxLayout()
        title = QLabel("🔌 Controller Configuration")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #f0f0f0;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        # Connection status indicator
        self.status_label = QLabel("⚫ Disconnected")
        self.status_label.setStyleSheet("""
            font-weight: bold;
            color: #e74c3c;
            background-color: #2a2323;
            padding: 5px 10px;
            border-radius: 3px;
            border: 1px solid #e74c3c;
        """)
        title_layout.addWidget(self.status_label)
        main_layout.addLayout(title_layout)
        
        # Connection Settings Group
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QGridLayout(connection_group)
        connection_layout.setSpacing(12)

        # Controller type
        self.controller_type = QComboBox()
        self.controller_type.addItems(["Arduino Uno", "Arduino Mega", "ESP32", "STM32", "Raspberry Pi", "Custom"])
        connection_layout.addWidget(QLabel("Controller:"), 0, 0)
        connection_layout.addWidget(self.controller_type, 0, 1)

        # Port selection with refresh button
        port_layout = QHBoxLayout()
        self.port_selector = QComboBox()
        self.btn_refresh_ports = QPushButton("🔄")
        self.btn_refresh_ports.setFixedSize(30, 30)
        self.btn_refresh_ports.setToolTip("Refresh available ports")
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        
        port_layout.addWidget(self.port_selector)
        port_layout.addWidget(self.btn_refresh_ports)
        connection_layout.addWidget(QLabel("Port:"), 1, 0)
        connection_layout.addLayout(port_layout, 1, 1)
        
        # Baudrate with custom option
        baudrate_layout = QHBoxLayout()
        self.baudrate_selector = QComboBox()
        self.baudrate_selector.setEditable(True)
        self.baudrate_selector.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "250000", "500000", "1000000"])
        self.baudrate_selector.setCurrentText("115200")
        baudrate_layout.addWidget(self.baudrate_selector)
        connection_layout.addWidget(QLabel("Baudrate:"), 2, 0)
        connection_layout.addLayout(baudrate_layout, 2, 1)
        
        # Advanced settings
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(1, 30)
        self.timeout_spinbox.setValue(5)
        self.timeout_spinbox.setSuffix(" sec")
        connection_layout.addWidget(QLabel("Timeout:"), 3, 0)
        connection_layout.addWidget(self.timeout_spinbox, 3, 1)
        
        # Auto-reconnect checkbox
        self.auto_reconnect = QCheckBox("Auto-reconnect on disconnect")
        self.auto_reconnect.setChecked(True)
        connection_layout.addWidget(self.auto_reconnect, 4, 0, 1, 2)
        
        main_layout.addWidget(connection_group)
        
        # Firmware Detection Group
        firmware_group = QGroupBox("Firmware Information")
        firmware_layout = QGridLayout(firmware_group)
        firmware_layout.setSpacing(12)
        
        self.firmware_label = QLabel("Not detected")
        self.firmware_label.setStyleSheet("""
            background-color: #232629;
            padding: 5px;
            border: 1px solid #444;
            border-radius: 3px;
            color: #f0f0f0;
        """)
        
        self.btn_detect_firmware = QPushButton("Detect Firmware")
        self.btn_detect_firmware.clicked.connect(self.detect_firmware)
        self.btn_detect_firmware.setEnabled(False)
        
        firmware_layout.addWidget(QLabel("Detected:"), 0, 0)
        firmware_layout.addWidget(self.firmware_label, 0, 1)
        firmware_layout.addWidget(self.btn_detect_firmware, 1, 0, 1, 2)
        
        main_layout.addWidget(firmware_group)
        
        # Connection Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_connect = QPushButton("🔗 Connect")
        self.btn_disconnect = QPushButton("🔌 Disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_reset = QPushButton("🔄 Reset")
        
        button_layout.addWidget(self.btn_connect)
        button_layout.addWidget(self.btn_disconnect)
        button_layout.addWidget(self.btn_reset)
        
        main_layout.addLayout(button_layout)
        
        # Connection Log
        log_group = QGroupBox("Connection Log")
        log_layout = QVBoxLayout(log_group)
        
        self.connection_log = QTextEdit()
        self.connection_log.setMaximumHeight(100)
        self.connection_log.setReadOnly(True)
        log_layout.addWidget(self.connection_log)
        
        main_layout.addWidget(log_group)
        main_layout.addStretch()
        
        # Connect signals
        self.btn_connect.clicked.connect(self.connect_to_controller)
        self.btn_disconnect.clicked.connect(self.disconnect_from_controller)
        self.btn_reset.clicked.connect(self.reset_connection)
        
        # Initialize ports
        self.refresh_ports()
    
    def setup_serial_manager_connections(self):
        """Setup connections to SerialManager signals"""
        # Connection status changes
        self.serial_manager.connection_status_changed.connect(self.on_connection_status_changed)
        self.serial_manager.connection_info_updated.connect(self.on_connection_info_updated)
        
        # Data and responses
        self.serial_manager.raw_data_received.connect(self.on_raw_data_received)
        self.serial_manager.data_received.connect(self.on_structured_data_received)
        
        # Firmware detection
        self.serial_manager.firmware_detected.connect(self.on_firmware_detected)
        
        # Command tracking
        self.serial_manager.command_sent.connect(self.on_command_sent)
        self.serial_manager.command_queued.connect(self.on_command_queued)
        self.serial_manager.response_timeout.connect(self.on_response_timeout)
        
        # Error handling
        self.serial_manager.error_occurred.connect(self.on_error_occurred)
    
    def setup_timers(self):
        # Auto-refresh ports every 5 seconds
        self.port_refresh_timer.timeout.connect(self.refresh_ports)
        self.port_refresh_timer.start(5000)
        
        # Connection monitoring timer
        self.connection_timer.timeout.connect(self.check_connection_status)
    
    def log_message(self, message):
        """Add message to connection log"""
        timestamp = time.strftime("%H:%M:%S")
        self.connection_log.append(f"[{timestamp}] {message}")
        self.connection_log.verticalScrollBar().setValue(
            self.connection_log.verticalScrollBar().maximum()
        )

    def refresh_ports(self):
        """Auto-detect serial ports and populate dropdown using SerialManager"""
        current_port = self.port_selector.currentData()
        ports = self.serial_manager.get_available_ports()
        
        self.port_selector.clear()
        available_ports = []
        
        for port_info in ports:
            port_name, description, hwid = port_info
            display_text = port_name
            if description and description != "n/a":
                display_text += f" - {description}"
            
            self.port_selector.addItem(display_text, port_name)
            available_ports.append(port_name)
        
        if not available_ports:
            self.port_selector.addItem("No devices found", "")
            self.log_message("No serial devices detected")
        else:
            self.log_message(f"Found {len(available_ports)} serial device(s)")
            
        # Restore previous selection if still available
        if current_port and current_port in available_ports:
            index = self.port_selector.findData(current_port)
            if index >= 0:
                self.port_selector.setCurrentIndex(index)
    
    def connect_to_controller(self):
        """Establish connection to the selected controller using SerialManager"""
        port = self.port_selector.currentData()
        baudrate = self.baudrate_selector.currentText()
        timeout = self.timeout_spinbox.value()

        if not port or not port.strip():
            QMessageBox.warning(self, "Connection Error", "Please select a valid port.")
            return

        # Validate baudrate
        try:
            baudrate_int = int(baudrate)
        except ValueError:
            QMessageBox.warning(self, "Connection Error", "Please enter a valid baudrate.")
            return

        self.log_message(f"Attempting to connect to {port} at {baudrate} baud...")
        
        # Show progress and disable UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.btn_connect.setEnabled(False)
        
        # Use SerialManager to connect
        success = self.serial_manager.connect(
            port_name=port,
            baudrate=baudrate_int,
            timeout=timeout,
            write_timeout=timeout
        )
        
        if not success:
            # Connection failed, UI will be updated via signal
            self.progress_bar.setVisible(False)
            self.btn_connect.setEnabled(True)
        
        self.save_connection_config()
    
    @Slot(ConnectionState)
    def on_connection_status_changed(self, state: ConnectionState):
        """Handle connection state changes from SerialManager"""
        self.progress_bar.setVisible(False)
        
        if state == ConnectionState.CONNECTED:
            self.is_connected = True
            self.status_label.setText("🟢 Connected")
            self.status_label.setStyleSheet("""
                font-weight: bold;
                color: #27ae60;
                background-color: #23292a;
                padding: 5px 10px;
                border-radius: 3px;
                border: 1px solid #27ae60;
            """)
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.btn_detect_firmware.setEnabled(True)
            self.connection_timer.start(1000)  # Check connection every second
            self.log_message("Successfully connected to controller")
            self.connection_status_changed.emit(True)
            
        elif state == ConnectionState.DISCONNECTED:
            self.is_connected = False
            self.status_label.setText("⚫ Disconnected")
            self.status_label.setStyleSheet("""
                font-weight: bold;
                color: #e74c3c;
                background-color: #2a2323;
                padding: 5px 10px;
                border-radius: 3px;
                border: 1px solid #e74c3c;
            """)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.btn_detect_firmware.setEnabled(False)
            self.connection_timer.stop()
            self.log_message("Disconnected from controller")
            self.connection_status_changed.emit(False)
            
        elif state == ConnectionState.CONNECTING:
            self.status_label.setText("🟡 Connecting...")
            self.status_label.setStyleSheet("""
                font-weight: bold;
                color: #f39c12;
                background-color: #2a2a23;
                padding: 5px 10px;
                border-radius: 3px;
                border: 1px solid #f39c12;
            """)
            
        elif state == ConnectionState.RECONNECTING:
            self.status_label.setText("🟡 Reconnecting...")
            self.status_label.setStyleSheet("""
                font-weight: bold;
                color: #f39c12;
                background-color: #2a2a23;
                padding: 5px 10px;
                border-radius: 3px;
                border: 1px solid #f39c12;
            """)
            self.log_message("Attempting to reconnect...")
            
        elif state == ConnectionState.ERROR:
            self.is_connected = False
            self.status_label.setText("🔴 Error")
            self.status_label.setStyleSheet("""
                font-weight: bold;
                color: #e74c3c;
                background-color: #2a2323;
                padding: 5px 10px;
                border-radius: 3px;
                border: 1px solid #e74c3c;
            """)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.btn_detect_firmware.setEnabled(False)
            self.connection_timer.stop()
            self.connection_status_changed.emit(False)
    
    @Slot(object)  # ConnectionInfo
    def on_connection_info_updated(self, connection_info):
        """Handle connection information updates"""
        # Update connection statistics if needed
        pass
    
    @Slot(str)
    def on_raw_data_received(self, data: str):
        """Handle raw data received from SerialManager"""
        self.log_message(f"Received: {data}")
        # Firmware detection using FirmwareUtils
        fw_type = self.firmware_utils.detect_firmware_type(data)
        if fw_type != FirmwareType.UNKNOWN:
            info = self.firmware_utils.extract_firmware_info(data)
            self.firmware_label.setText(f"{info.name} v{info.version}")
            self.firmware_label.setToolTip(self.firmware_utils.format_firmware_info(info))
    
    @Slot(object)  # SerialResponse
    def on_structured_data_received(self, response: SerialResponse):
        """Handle structured response data from SerialManager"""
        # Handle different response types
        if response.response_type == 'error':
            self.log_message(f"Error: {response.raw_data}")
        elif response.response_type == 'status':
            self.log_message(f"Status: {response.raw_data}")
        elif response.response_type == 'firmware':
            self.log_message(f"Firmware: {response.raw_data}")
        # Firmware detection using FirmwareUtils (in addition to SerialManager)
        fw_type = self.firmware_utils.detect_firmware_type(response.raw_data)
        if fw_type != FirmwareType.UNKNOWN:
            info = self.firmware_utils.extract_firmware_info(response.raw_data)
            self.firmware_label.setText(f"{info.name} v{info.version}")
            self.firmware_label.setToolTip(self.firmware_utils.format_firmware_info(info))
    
    @Slot(FirmwareType, dict)
    def on_firmware_detected(self, firmware_type: FirmwareType, firmware_info: dict):
        """Handle firmware detection from SerialManager"""
        firmware_name = firmware_type.value
        self.firmware_label.setText(firmware_name)
        
        if firmware_type != FirmwareType.UNKNOWN:
            self.firmware_label.setStyleSheet("""
                background-color: #23292a;
                color: #27ae60;
                padding: 5px;
                border: 1px solid #27ae60;
                border-radius: 3px;
                font-weight: bold;
            """)
        self.log_message(f"Detected firmware: {firmware_name}")
    
    @Slot(str)
    def on_command_sent(self, command: str):
        """Handle command sent notification"""
        self.log_message(f"Sent: {command}")
    
    @Slot(str)
    def on_command_queued(self, command: str):
        """Handle command queued notification"""
        # Optional: log queued commands
        pass
    
    @Slot(str)
    def on_response_timeout(self, command: str):
        """Handle command timeout"""
        self.log_message(f"Timeout: {command}")
    
    @Slot(str)
    def on_error_occurred(self, error: str):
        """Handle errors from SerialManager"""
        self.log_message(f"Error: {error}")
    
    def disconnect_from_controller(self):
        """Disconnect from the controller using SerialManager"""
        self.serial_manager.disconnect()
        # UI will be updated via connection_status_changed signal
        
        self.save_connection_config()
    
    def detect_firmware(self):
        """Manually trigger firmware detection using SerialManager"""
        if self.serial_manager.is_connected():
            # Send firmware detection commands
            self.serial_manager.send_command("M115", priority=1)
            self.serial_manager.send_command("$I", priority=1)
            self.log_message("Sending firmware detection commands...")
    
    def reset_connection(self):
        """Reset connection settings to defaults"""
        if self.is_connected:
            reply = QMessageBox.question(
                self, "Reset Connection", 
                "This will disconnect the current connection. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            self.disconnect_from_controller()
        
        # Reset to defaults
        self.controller_type.setCurrentIndex(0)
        self.baudrate_selector.setCurrentText("115200")
        self.timeout_spinbox.setValue(5)
        self.auto_reconnect.setChecked(True)
        self.firmware_label.setText("Not detected")
        self.firmware_label.setStyleSheet("""
            background-color: #232629;
            padding: 5px;
            border: 1px solid #444;
            border-radius: 3px;
            color: #f0f0f0;
        """)
        self.connection_log.clear()
        self.refresh_ports()
        self.log_message("Connection settings reset to defaults")
        
        self.save_connection_config()
    
    def check_connection_status(self):
        """Periodically check if connection is still active"""
        if not self.serial_manager.is_connected():
            if self.auto_reconnect.isChecked():
                self.log_message("Connection lost, attempting to reconnect...")
                # SerialManager will handle reconnection automatically
            else:
                self.disconnect_from_controller()
                QMessageBox.warning(self, "Connection Lost", "Connection to controller was lost.")
    
    def send_command(self, command: str) -> bool:
        """Send a command to the connected controller using SerialManager"""
        if self.serial_manager.is_connected():
            command_id = self.serial_manager.send_command(command)
            return command_id is not None
        return False
    
    def get_connection_status(self) -> bool:
        """Return current connection status"""
        return self.serial_manager.is_connected()
    
    def get_connection_info(self):
        """Get detailed connection information"""
        return self.serial_manager.get_connection_info()
    
    def get_firmware_info(self):
        """Return the current firmware info as a dict."""
        return self.firmware_utils.export_firmware_info()
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.serial_manager.cleanup()
        self.port_refresh_timer.stop()
        self.connection_timer.stop()
        event.accept()

    def apply_styles(self):
        """Apply dark theme styling to match global design"""
        self.setStyleSheet("""
            QWidget {
                background-color: #232629;
                color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1.5px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #282c34;
                color: #f0f0f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #f0f0f0;
            }
            QLabel {
                color: #f0f0f0;
            }
            QComboBox {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 6px 8px;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #1976d2;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background-color: #232629;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #f0f0f0;
            }
            QComboBox QAbstractItemView {
                background-color: #232629;
                color: #f0f0f0;
                border: 1px solid #444;
                selection-background-color: #1976d2;
            }
            QSpinBox {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 6px 8px;
                min-height: 20px;
            }
            QSpinBox:focus {
                border-color: #1976d2;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #232629;
                border: none;
                width: 16px;
            }
            QSpinBox::up-arrow {
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid #f0f0f0;
            }
            QSpinBox::down-arrow {
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #f0f0f0;
            }
            QCheckBox {
                color: #f0f0f0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1.5px solid #444;
                border-radius: 3px;
                background-color: #232629;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border-color: #1976d2;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton {
                background-color: #1976d2;
                border: none;
                border-radius: 6px;
                color: #f0f0f0;
                font-weight: bold;
                padding: 8px 16px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #115293;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #666;
            }
            QTextEdit {
                background-color: #232629;
                color: #f0f0f0;
                border: 1.5px solid #444;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
            QProgressBar {
                background-color: #232629;
                color: #f0f0f0;
                border: 1.5px solid #444;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1976d2;
                border-radius: 4px;
            }
        """)

    def load_connection_config(self):
        config = self.config_manager.get_connection_config()
        self.controller_type.setCurrentText(config.controller_type)
        self.baudrate_selector.setCurrentText(str(config.baudrate))
        self.timeout_spinbox.setValue(int(config.timeout))
        self.auto_reconnect.setChecked(config.auto_connect)
        self.refresh_ports()
        # Set the port after ports are loaded
        QTimer.singleShot(100, lambda: self.port_selector.setCurrentText(config.port))

    def save_connection_config(self):
        config = ConnectionConfig(
            controller_type=self.controller_type.currentText(),
            port=self.port_selector.currentText(),
            baudrate=int(self.baudrate_selector.currentText()),
            timeout=float(self.timeout_spinbox.value()),
            auto_connect=self.auto_reconnect.isChecked()
        )
        self.config_manager.set_connection_config(config)