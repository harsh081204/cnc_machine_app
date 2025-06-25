# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.log_panel import LogPanel
from ui.jog_panel import JogPanel
from ui.tab_config import ConfigTab
from ui.tab_actuators import ActuatorsTab
from ui.tab_connection import ConnectionTab
from ui.tab_console import ConsoleTab
from ui.tab_macros import MacroTab
from core.config_manager import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INVARIANCE AUTOMATION - CNC Controller")
        self.setMinimumSize(1200, 700)
        self.config_manager = ConfigManager()
        self.init_ui()
        self.setup_connections()
        # Apply UI settings from config_manager
        ui_config = self.config_manager.get_ui_config()
        if hasattr(ui_config, 'window_size'):
            self.resize(*ui_config.window_size)

    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Splitter to divide left and right panes
        splitter = QSplitter(Qt.Horizontal)

        # Left pane (log + jog)
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(10, 10, 10, 10)
        self.log_panel = LogPanel()
        self.jog_panel = JogPanel(config_manager=self.config_manager)
        left_layout.addWidget(self.log_panel)
        left_layout.addWidget(self.jog_panel)
        splitter.addWidget(left_pane)

        # Right pane with QTabWidget
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(10, 10, 10, 10)

        self.tab_widget = QTabWidget()
        self.config_tab = ConfigTab(config_manager=self.config_manager)
        self.actuators_tab = ActuatorsTab(config_manager=self.config_manager)
        self.connection_tab = ConnectionTab(config_manager=self.config_manager)
        self.console_tab = ConsoleTab()
        self.macros_tab = MacroTab(self.connection_tab.serial_manager)
        
        self.tab_widget.addTab(self.config_tab, "Configuration")
        self.tab_widget.addTab(self.actuators_tab, "Actuators")
        self.tab_widget.addTab(self.connection_tab, "Connection")
        self.tab_widget.addTab(self.console_tab, "Console")
        self.tab_widget.addTab(self.macros_tab, "Macros")

        right_layout.addWidget(self.tab_widget)
        splitter.addWidget(right_pane)

        # Set stretch (40/60 split)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

        # Live coordinates display (compact)
        self.coords_label = QLabel("X: 0.000  Y: 0.000  Z: 0.000")
        self.coords_label.setAlignment(Qt.AlignRight)
        self.coords_label.setStyleSheet("background-color: #222; color: #0fa; border: 1px solid #333; font: bold 10pt 'Consolas'; padding: 2px 8px; border-radius: 4px;")
        main_layout.addWidget(self.coords_label)

    def setup_connections(self):
        """Setup signal connections between components"""
        # Connect actuators tab signals
        self.actuators_tab.actuator_command_sent.connect(self.handle_actuator_command)
        self.actuators_tab.configuration_changed.connect(self.handle_actuator_config_changed)
        
        # Connect config tab signals
        self.config_tab.config_changed.connect(self.handle_config_changed)
        self.config_tab.config_saved.connect(self.handle_config_saved)
        
        # Connect connection tab signals
        self.connection_tab.connection_status_changed.connect(self.handle_connection_status)
        
        # Connect console tab signals
        self.console_tab.command_sent.connect(self.handle_console_command)
        
        # Connect jog panel signals
        self.jog_panel.jog_requested.connect(self.handle_jog_request)
        self.jog_panel.home_requested.connect(self.handle_home_request)
        self.jog_panel.park_requested.connect(self.handle_park_request)
        self.jog_panel.start_requested.connect(self.handle_start_request)
        self.jog_panel.emergency_stop_requested.connect(self.handle_emergency_stop)
        # Connect live coordinates
        self.connection_tab.serial_manager.coordinates_updated.connect(self.update_coordinates_display)
        # Macro execution feedback
        self.macros_tab.macro_executed.connect(self.handle_macro_executed)

    def handle_actuator_command(self, command: str):
        """Handle actuator command from actuators tab"""
        self.log_panel.append_log(f"Actuator Command: {command}")
        # Send command via connection tab if connected
        if self.connection_tab.get_connection_status():
            success = self.connection_tab.send_command(command)
            if not success:
                self.log_panel.append_log("Failed to send actuator command - not connected")
        else:
            self.log_panel.append_log("Cannot send actuator command - not connected")

    def handle_actuator_config_changed(self):
        """Handle actuator configuration changes"""
        self.log_panel.append_log("Actuator configuration modified")

    def handle_config_changed(self, config: dict):
        """Handle configuration changes from config tab"""
        self.log_panel.append_log("Axis configuration modified")

    def handle_config_saved(self, config: dict):
        """Handle configuration save from config tab"""
        self.log_panel.append_log("Axis configuration saved")

    def handle_connection_status(self, connected: bool):
        """Handle connection status change from connection tab"""
        status = "Connected" if connected else "Disconnected"
        self.log_panel.append_log(f"Controller {status}")
        
        # Enable/disable controls based on connection status
        self.jog_panel.set_enabled_state(connected)
        
        # Update console tab with connection status
        if hasattr(self.console_tab, 'set_connection_status'):
            self.console_tab.set_connection_status(connected)

    def handle_console_command(self, command: str):
        """Handle console command from console tab"""
        self.log_panel.append_log(f"Console Command: {command}")
        # Send command to CNC controller via connection tab
        if self.connection_tab.get_connection_status():
            success = self.connection_tab.send_command(command)
            if not success:
                self.log_panel.append_log("Failed to send console command")
        else:
            self.log_panel.append_log("Cannot send console command - not connected")

    def handle_jog_request(self, direction: str, distance: float):
        """Handle jog movement request"""
        self.log_panel.append_log(f"Jog: {direction} {distance}mm")
        # Send jog command to CNC controller via connection tab
        if self.connection_tab.get_connection_status():
            # Convert jog request to appropriate G-code command
            command = self.convert_jog_to_gcode(direction, distance)
            if command:
                success = self.connection_tab.send_command(command)
                if not success:
                    self.log_panel.append_log("Failed to send jog command")
        else:
            self.log_panel.append_log("Cannot send jog command - not connected")

    def handle_home_request(self):
        """Handle home request"""
        self.log_panel.append_log("Home request")
        # Send home command to CNC controller via connection tab
        if self.connection_tab.get_connection_status():
            success = self.connection_tab.send_command("G28 Z")
            success = self.connection_tab.send_command("G0 Z-27")
            success = self.connection_tab.send_command("G92 Z0")
            success = self.connection_tab.send_command("G28 X Y")  
            success = self.connection_tab.send_command("G92 X250 Y250")# Standard home command
            if not success:
                self.log_panel.append_log("Failed to send home command")
        else:
            self.log_panel.append_log("Cannot send home command - not connected")

    def handle_park_request(self):
        """Handle park request"""
        self.log_panel.append_log("Park request")
        # Send park command to CNC controller via connection tab
        if self.connection_tab.get_connection_status():
            # Park command varies by firmware, try common ones
            park_commands = ["G28", "G0 Z10", "G0 X0 Y0 Z10"]
            for cmd in park_commands:
                success = self.connection_tab.send_command(cmd)
                if success:
                    break
            if not success:
                self.log_panel.append_log("Failed to send park command")
        else:
            self.log_panel.append_log("Cannot send park command - not connected")

    def handle_start_request(self):
        """Handle start request"""
        self.log_panel.append_log("Start request")
        # Send start command to CNC controller via connection tab
        if self.connection_tab.get_connection_status():
            success = self.connection_tab.send_command("M3 S1000")  # Start spindle
            if not success:
                self.log_panel.append_log("Failed to send start command")
        else:
            self.log_panel.append_log("Cannot send start command - not connected")

    def handle_emergency_stop(self):
        """Handle emergency stop request"""
        self.log_panel.append_log("EMERGENCY STOP!")
        # Send emergency stop command to CNC controller via connection tab
        if self.connection_tab.get_connection_status():
            # Send multiple emergency commands to ensure stop
            emergency_commands = ["M112", "M0", "!", "X"]  # Emergency stop, program stop, feed hold, etc.
            for cmd in emergency_commands:
                self.connection_tab.send_command(cmd)
            self.log_panel.append_log("Emergency stop commands sent")
        else:
            self.log_panel.append_log("Cannot send emergency stop - not connected")

    def convert_jog_to_gcode(self, direction: str, distance: float) -> str:
        """Convert jog direction and distance to G-code command"""
        # Get current position or use relative positioning
        if direction == "X+":
            return f"G91\n G0 X{distance}\n G90"  # Relative move X positive
        elif direction == "X-":
            return f"G91\n G0 X-{distance}\n G90"  # Relative move X negative
        elif direction == "Y+":
            return f"G91\n G0 Y{distance}\n G90"  # Relative move Y positive
        elif direction == "Y-":
            return f"G91\n G0 Y-{distance}\n G90"  # Relative move Y negative
        elif direction == "Z+":
            return f"G91\n G0 Z{distance}\n G90"  # Relative move Z positive
        elif direction == "Z-":
            return f"G91\n G0 Z-{distance}\n G90"  # Relative move Z negative
        elif direction == "XY_HOME":
            return "G28 X Y"  # Home X and Y axes
        elif direction == "Z_HOME":
            return "G28 Z"  # Home Z axis
        else:
            return None

    def get_connection_info(self):
        """Get detailed connection information"""
        return self.connection_tab.get_connection_info()

    def get_firmware_info(self):
        """Get firmware information"""
        return self.connection_tab.get_firmware_info()

    def update_coordinates_display(self, coords):
        self.coords_label.setText(f"X: {coords.get('X', 0.0):.3f}  Y: {coords.get('Y', 0.0):.3f}  Z: {coords.get('Z', 0.0):.3f}")

    def handle_macro_executed(self, gcode):
        name = self.macros_tab.macro_name.text().strip()
        self.log_panel.append_log(f"Macro Executed: <b>{name}</b>")
        self.log_panel.append_log(f"<pre style='color:#0af;'>{gcode}</pre>")

    def closeEvent(self, event):
        # Save UI settings to config_manager
        size = self.size()
        ui_config = self.config_manager.get_ui_config()
        ui_config.window_size = (size.width(), size.height())
        self.config_manager.set_ui_config(ui_config)
        # Clean up connections
        if hasattr(self.connection_tab, 'serial_manager'):
            self.connection_tab.serial_manager.cleanup()
        
        # Close the application
        event.accept()
