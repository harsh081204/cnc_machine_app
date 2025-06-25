# ui/tab_console.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QLineEdit,
    QSplitter, QMessageBox, QInputDialog, QGroupBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QFont
import json
import time


class ConsoleTab(QWidget):
    command_sent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.micros = {}
        self.settings = QSettings("CNCApp", "Console")
        self.is_connected = False  # Track connection status
        self.init_ui()
        self.setup_connections()
        self.load_micros()
        self.apply_styles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Title section
        self.create_title_section(main_layout)

        # Console section only (no splitter, no micros)
        console_widget = self.create_console_section()
        main_layout.addWidget(console_widget)

    def create_title_section(self, parent_layout):
        """Create the title section"""
        title_frame = QFrame()
        title_frame.setFrameStyle(QFrame.Box)
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #282c34;
                border: 1.5px solid #444;
                border-radius: 8px;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        
        title = QLabel("🖥 Console")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #f0f0f0;")
        title_layout.addWidget(title)
        
        parent_layout.addWidget(title_frame)

    def create_console_section(self):
        """Create the console input and output section"""
        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)
        console_layout.setSpacing(12)

        # Command input section
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Type G-code or command here...")
        self.command_input.returnPressed.connect(self.send_command)
        
        self.btn_send = QPushButton("Send")
        self.btn_send.setMinimumWidth(80)
        
        input_layout.addWidget(self.command_input)
        input_layout.addWidget(self.btn_send)
        console_layout.addLayout(input_layout)

        # Console output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setMinimumHeight(200)
        console_layout.addWidget(self.console_output)

        return console_group

    def setup_connections(self):
        """Setup signal connections"""
        self.btn_send.clicked.connect(self.send_command)

    def send_command(self):
        """Send command from console input"""
        cmd = self.command_input.text().strip()
        if not cmd:
            return
        
        timestamp = time.strftime("%H:%M:%S")
        self.console_output.append(f'<span style="color: #3498db;">[{timestamp}] > {cmd}</span>')
        self.command_input.clear()
        self.command_sent.emit(cmd)

    def load_micros(self):
        """Load micros from settings"""
        try:
            micros_json = self.settings.value("micros", "{}")
            self.micros = json.loads(micros_json)
            self.log_message("Micros loaded successfully")
        except Exception as e:
            self.log_message(f"Load failed: {str(e)}")
            self.micros = {}

    def log_message(self, message: str):
        """Add message to console output"""
        timestamp = time.strftime("%H:%M:%S")
        self.console_output.append(f'<span style="color: #95a5a6;">[{timestamp}] {message}</span>')

    def append_response(self, response: str):
        """Append response from controller to console"""
        timestamp = time.strftime("%H:%M:%S")
        self.console_output.append(f'<span style="color: #27ae60;">[{timestamp}] {response}</span>')

    def set_connection_status(self, connected: bool):
        """Update connection status and enable/disable controls accordingly"""
        self.is_connected = connected
        
        # Update command input placeholder
        if connected:
            self.command_input.setPlaceholderText("Type G-code or command here...")
            self.btn_send.setEnabled(True)
            self.log_message("Console connected to controller")
        else:
            self.command_input.setPlaceholderText("Not connected - commands will not be sent")
            self.btn_send.setEnabled(False)
            self.log_message("Console disconnected from controller")

    def apply_styles(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
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
            QLineEdit {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 6px 8px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #1976d2;
            }
            QTextEdit {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
            QListWidget {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                alternate-background-color: #282c34;
                color: #f0f0f0;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #1976d2;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #2c3e50;
            }
            QPushButton {
                background-color: #1976d2;
                border: none;
                border-radius: 6px;
                color: #f0f0f0;
                font-weight: bold;
                padding: 8px 12px;
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
            QLabel {
                color: #f0f0f0;
            }
        """)
