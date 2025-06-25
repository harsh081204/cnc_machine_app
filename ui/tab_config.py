# ui/tab_config.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QScrollArea, QGroupBox, QMessageBox, QProgressBar, QFrame, QListWidget, QStackedWidget
)
from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtGui import QFont, QIcon
from ui.components.axis_config_widget import AxisConfigWidget
import json
import logging
from core.config_manager import AxisConfig
import traceback

class ConfigTab(QWidget):
    # Signals for parent communication
    config_changed = Signal(dict)  # Emitted when config is modified
    config_saved = Signal(dict)    # Emitted when config is saved
    config_reset = Signal()        # Emitted when config is reset
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.is_modified = False
        self.init_ui()
        self.connect_signals()
        self.load_config_from_manager()
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # Header section
        header_frame = self.create_header()
        main_layout.addWidget(header_frame)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # Axis configuration group
        axis_group = self.create_axis_group()
        scroll_layout.addWidget(axis_group)
        
        # Advanced settings group (expandable)
        advanced_group = self.create_advanced_group()
        scroll_layout.addWidget(advanced_group)
        
        # Add stretch to push everything to top
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Status bar
        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)
        
        # Button panel
        button_panel = self.create_button_panel()
        main_layout.addWidget(button_panel)
    
    def create_header(self):
        """Create header with title and status indicator"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)
        
        # Title with icon
        title = QLabel("⚙️ Axis Configuration")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        
        # Status indicator
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.status_label)
        
        return frame
    
    def create_axis_group(self):
        """Create axis configuration group with sidebar and stacked widget"""
        group = QGroupBox("Axis Parameters")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #232629;
                color: #f0f0f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """)
        layout = QHBoxLayout(group)
        layout.setSpacing(16)

        # Sidebar for axis selection
        self.axis_list = QListWidget()
        self.axis_list.setFixedWidth(100)
        self.axis_list.addItem("X Axis")
        self.axis_list.addItem("Y Axis")
        self.axis_list.addItem("Z Axis")
        layout.addWidget(self.axis_list)

        # Stacked widget for per-axis settings
        self.axis_stack = QStackedWidget()
        self.axis_x = AxisConfigWidget("X Axis", color="#FF6B6B")
        self.axis_y = AxisConfigWidget("Y Axis", color="#4ECDC4")
        self.axis_z = AxisConfigWidget("Z Axis", color="#45B7D1")
        self.axis_stack.addWidget(self.axis_x)
        self.axis_stack.addWidget(self.axis_y)
        self.axis_stack.addWidget(self.axis_z)
        layout.addWidget(self.axis_stack)

        # Connect sidebar to stacked widget
        self.axis_list.currentRowChanged.connect(self.axis_stack.setCurrentIndex)
        self.axis_list.setCurrentRow(0)

        return group
    
    def create_advanced_group(self):
        """Create advanced settings group (collapsible)"""
        group = QGroupBox("Advanced Settings")
        group.setCheckable(True)
        group.setChecked(False)  # Collapsed by default
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #232629;
                color: #f0f0f0;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # Add advanced settings here (placeholder)
        advanced_label = QLabel("Advanced axis settings will be implemented here")
        advanced_label.setStyleSheet("color: #b0b0b0; font-style: italic;")
        layout.addWidget(advanced_label)
        
        return group
    
    def create_status_bar(self):
        """Create status bar with progress indicator"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(6)
        
        layout.addWidget(self.progress_bar)
        
        return frame
    
    def create_button_panel(self):
        """Create enhanced button panel"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left side buttons
        self.btn_load = QPushButton("📂 Load Config")
        self.btn_export = QPushButton("📤 Export")
        
        # Right side buttons
        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_save = QPushButton("💾 Save")
        
        # Style buttons
        button_style = """
            QPushButton {
                padding: 8px 16px;
                border: 2px solid #444;
                border-radius: 6px;
                background-color: #232629;
                font-weight: bold;
                color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #1976d2;
                border-color: #1976d2;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #115293;
            }
        """
        
        # Apply styles and set initial states
        for btn in [self.btn_load, self.btn_export, self.btn_reset, self.btn_save]:
            btn.setStyleSheet(button_style)
        
        # Save button special styling when modified
        self.btn_save.setStyleSheet(button_style + """
            QPushButton[modified="true"] {
                background-color: #28a745;
                color: white;
                border-color: #28a745;
            }
        """)
        
        # Layout buttons
        layout.addWidget(self.btn_load)
        layout.addWidget(self.btn_export)
        layout.addStretch()
        layout.addWidget(self.btn_reset)
        layout.addWidget(self.btn_save)
        
        return frame
    
    def connect_signals(self):
        """Connect all widget signals"""
        # Button connections
        self.btn_save.clicked.connect(self.save_config)
        self.btn_reset.clicked.connect(self.reset_config)
        self.btn_load.clicked.connect(self.load_config)
        self.btn_export.clicked.connect(self.export_config)
        
        # Axis widget connections
        for axis in [self.axis_x, self.axis_y, self.axis_z]:
            axis.config_changed.connect(self.on_config_modified)
            axis.validation_error.connect(self.on_validation_error)
    
    def on_config_modified(self):
        """Handle when any configuration is modified"""
        self.is_modified = True
        self.status_label.setText("● Modified")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        self.btn_save.setProperty("modified", "true")
        self.btn_save.style().polish(self.btn_save)
        
        # Emit signal with current config
        config = self.get_current_config()
        self.config_changed.emit(config)
    
    def on_validation_error(self, error_msg):
        """Handle validation errors from axis widgets"""
        self.status_label.setText(f"⚠️ {error_msg}")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def save_config(self):
        """Save current configuration"""
        if not self.validate_all_configs():
            QMessageBox.warning(self, "Validation Error", "Please fix validation errors before saving.")
            return
        try:
            self.show_progress("Saving configuration...")
            # Save each axis config
            for axis, widget in zip(['x', 'y', 'z'], [self.axis_x, self.axis_y, self.axis_z]):
                config = widget.get_config()
                print(f"[DEBUG] Saving axis {axis}: {config}")
                axis_fields = set(AxisConfig.__dataclass_fields__.keys())
                filtered_config = {k: v for k, v in config.items() if k in axis_fields}
                self.config_manager.set_axis_config(axis, AxisConfig(**filtered_config))
            QTimer.singleShot(1000, lambda: self.save_complete(self.get_current_config()))
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            print(f"[ERROR] Exception in save_config: {e}")
            print(traceback.format_exc())
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}\n\n{traceback.format_exc()}")
            self.hide_progress()
    
    def save_complete(self, config):
        """Complete the save operation"""
        self.hide_progress()
        self.is_modified = False
        self.status_label.setText("✅ Saved")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.btn_save.setProperty("modified", "false")
        self.btn_save.style().polish(self.btn_save)
        
        self.config_saved.emit(config)
        
        # Reset status after 3 seconds
        QTimer.singleShot(3000, lambda: self.reset_status())
    
    def reset_config(self):
        """Reset configuration to defaults"""
        reply = QMessageBox.question(self, "Reset Configuration",
                                   "Are you sure you want to reset all settings to default values?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.load_default_config()
            self.config_reset.emit()
            self.status_label.setText("🔄 Reset to defaults")
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
    
    def load_config(self):
        """Load configuration from file"""
        # Placeholder for file dialog and loading logic
        QMessageBox.information(self, "Load Config", "Load configuration feature will be implemented")
    
    def export_config(self):
        """Export current configuration"""
        # Placeholder for export logic
        QMessageBox.information(self, "Export Config", "Export configuration feature will be implemented")
    
    def get_current_config(self):
        """Get current configuration from all axis widgets"""
        return {
            'x_axis': self.axis_x.get_config(),
            'y_axis': self.axis_y.get_config(),
            'z_axis': self.axis_z.get_config(),
            'timestamp': self.get_timestamp()
        }
    
    def load_config_from_manager(self):
        """Load axis config from ConfigManager and populate widgets"""
        for axis, widget in zip(['x', 'y', 'z'], [self.axis_x, self.axis_y, self.axis_z]):
            axis_config = self.config_manager.get_axis_config(axis)
            widget.set_config(axis_config.__dict__)
    
    def load_default_config(self):
        """Load default configuration values (from config manager)"""
        self.load_config_from_manager()
        self.is_modified = False
        self.reset_status()
    
    def validate_all_configs(self):
        """Validate all axis configurations"""
        return (self.axis_x.validate() and 
                self.axis_y.validate() and 
                self.axis_z.validate())
    
    def show_progress(self, message):
        """Show progress indicator"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
    
    def hide_progress(self):
        """Hide progress indicator"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 1)
    
    def reset_status(self):
        """Reset status to ready state"""
        self.status_label.setText("● Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
    
    def get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def set_config(self, config_dict):
        """Set configuration from external source"""
        try:
            if 'x_axis' in config_dict:
                self.axis_x.set_config(config_dict['x_axis'])
            if 'y_axis' in config_dict:
                self.axis_y.set_config(config_dict['y_axis'])
            if 'z_axis' in config_dict:
                self.axis_z.set_config(config_dict['z_axis'])
            
            self.is_modified = False
            self.reset_status()
            
        except Exception as e:
            self.logger.error(f"Error setting config: {e}")
            QMessageBox.critical(self, "Config Error", f"Failed to load configuration:\n{e}")