# ui/tab_actuators.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QMessageBox, QFrame, QListWidgetItem, QSplitter, QTextEdit,
    QGroupBox, QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QFont, QIcon, QAction
from ui.components.actuator_dialog import ActuatorDialog
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from core.config_manager import ConfigManager


@dataclass
class ActuatorConfig:
    """Configuration data for an actuator"""
    name: str
    enabled: bool = True
    command_template: str = "G55 P{id} S{state};"
    description: str = ""
    pin: int = 0
    inverted: bool = False


class ActuatorListWidget(QListWidget):
    """Enhanced list widget with context menu support"""
    
    actuator_renamed = Signal(str, str)  # old_name, new_name
    actuator_deleted = Signal(str)  # name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, position):
        """Show context menu for actuator management"""
        item = self.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self.rename_actuator(item))
        menu.addAction(rename_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_actuator(item))
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def rename_actuator(self, item):
        """Rename an actuator"""
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "Rename Actuator", "Enter new name:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            item.setText(new_name)
            self.actuator_renamed.emit(old_name, new_name)
    
    def delete_actuator(self, item):
        """Delete an actuator"""
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Actuator",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            row = self.row(item)
            self.takeItem(row)
            self.actuator_deleted.emit(name)


class ActuatorPreviewWidget(QWidget):
    """Widget to preview actuator configuration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.current_config = None
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Actuator Preview")
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #f0f0f0;")
        layout.addWidget(title)
        
        # Preview content
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setStyleSheet("""
            QTextEdit {
                border: 1.5px solid #444;
                border-radius: 6px;
                background-color: #232629;
                color: #f0f0f0;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        layout.addWidget(self.preview_text)
        
        # Command input section
        command_group = QGroupBox("Command Input")
        command_layout = QVBoxLayout(command_group)
        
        # ON command input
        on_layout = QHBoxLayout()
        on_layout.addWidget(QLabel("ON Command:"))
        self.on_command_input = QLineEdit()
        self.on_command_input.setPlaceholderText("Enter ON command...")
        self.on_command_input.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 4px 8px;
            }
        """)
        on_layout.addWidget(self.on_command_input)
        command_layout.addLayout(on_layout)
        
        # OFF command input
        off_layout = QHBoxLayout()
        off_layout.addWidget(QLabel("OFF Command:"))
        self.off_command_input = QLineEdit()
        self.off_command_input.setPlaceholderText("Enter OFF command...")
        self.off_command_input.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 4px 8px;
            }
        """)
        off_layout.addWidget(self.off_command_input)
        command_layout.addLayout(off_layout)
        
        layout.addWidget(command_group)
        
        # Test buttons
        test_layout = QHBoxLayout()
        self.btn_test_on = QPushButton("Test ON")
        self.btn_test_off = QPushButton("Test OFF")
        
        test_layout.addWidget(self.btn_test_on)
        test_layout.addWidget(self.btn_test_off)
        layout.addLayout(test_layout)
        
        self.clear_preview()
    
    def update_preview(self, config: ActuatorConfig):
        """Update the preview with actuator configuration"""
        self.current_config = config
        
        preview_text = f"""
<b>Name:</b> {config.name}<br>
<b>Enabled:</b> {"Yes" if config.enabled else "No"}<br>
<b>Pin:</b> {config.pin}<br>
<b>Inverted:</b> {"Yes" if config.inverted else "No"}<br>
<b>Description:</b> {config.description or "None"}<br>
<br>
<b>Command Template:</b><br>
<code>{config.command_template}</code>
        """
        
        self.preview_text.setHtml(preview_text)
        
        # Populate command inputs with generated commands
        on_command = self.generate_example_command(config, True)
        off_command = self.generate_example_command(config, False)
        
        self.on_command_input.setText(on_command)
        self.off_command_input.setText(off_command)
        
        self.btn_test_on.setEnabled(config.enabled)
        self.btn_test_off.setEnabled(config.enabled)
    
    def generate_example_command(self, config: ActuatorConfig, state: bool) -> str:
        """Generate example command based on template"""
        try:
            # Simple template substitution
            cmd = config.command_template
            cmd = cmd.replace("{id}", str(config.pin))
            cmd = cmd.replace("{name}", config.name)
            
            # Handle state logic
            if config.inverted:
                state = not state
            
            cmd = cmd.replace("{state}", "1" if state else "0")
            cmd = cmd.replace("{true:255}", "255" if state else "0")
            cmd = cmd.replace("{false:0}", "0" if not state else "255")
            
            return cmd
        except Exception:
            return "Invalid template"
    
    def clear_preview(self):
        """Clear the preview"""
        self.preview_text.setHtml("<i>Select an actuator to preview its configuration</i>")
        self.on_command_input.clear()
        self.off_command_input.clear()
        self.btn_test_on.setEnabled(False)
        self.btn_test_off.setEnabled(False)
        self.current_config = None


class ActuatorsTab(QWidget):
    """Enhanced Actuators Tab with full configuration management"""
    
    # Signals
    actuator_command_sent = Signal(str)  # command
    configuration_changed = Signal()
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.actuator_configs: Dict[str, ActuatorConfig] = {}
        self.init_ui()
        self.setup_connections()
        self.load_configuration()
        self.apply_styles()
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Title section
        self.create_title_section(main_layout)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Actuator list and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview and configuration
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([250, 350])
        main_layout.addWidget(splitter)
        
        # Bottom button panel
        self.create_bottom_panel(main_layout)
    
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
        
        title = QLabel("Actuator Command Configuration")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #f0f0f0;")
        title_layout.addWidget(title)
        
        parent_layout.addWidget(title_frame)
    
    def create_left_panel(self):
        """Create the left panel with actuator list and controls"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Actuator count control
        count_group = QGroupBox("Actuator Count")
        count_layout = QHBoxLayout(count_group)
        
        count_layout.addWidget(QLabel("Number of actuators:"))
        self.actuator_count_spin = QSpinBox()
        self.actuator_count_spin.setRange(1, 20)
        self.actuator_count_spin.setValue(3)
        count_layout.addWidget(self.actuator_count_spin)
        
        self.btn_update_count = QPushButton("Update")
        count_layout.addWidget(self.btn_update_count)
        
        left_layout.addWidget(count_group)
        
        # Actuator list
        list_group = QGroupBox("Actuators")
        list_layout = QVBoxLayout(list_group)
        
        self.actuator_list = ActuatorListWidget()
        self.actuator_list.setAlternatingRowColors(True)
        list_layout.addWidget(self.actuator_list)
        
        # List control buttons
        list_btn_layout = QHBoxLayout()
        self.btn_add_actuator = QPushButton("Add")
        self.btn_edit_actuator = QPushButton("Edit")
        self.btn_duplicate_actuator = QPushButton("Duplicate")
        
        list_btn_layout.addWidget(self.btn_add_actuator)
        list_btn_layout.addWidget(self.btn_edit_actuator)
        list_btn_layout.addWidget(self.btn_duplicate_actuator)
        list_layout.addLayout(list_btn_layout)
        
        left_layout.addWidget(list_group)
        
        return left_widget
    
    def create_right_panel(self):
        """Create the right panel with preview"""
        self.preview_widget = ActuatorPreviewWidget()
        return self.preview_widget
    
    def create_bottom_panel(self, parent_layout):
        """Create the bottom control panel"""
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.StyledPanel)
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: #282c34;
                border: 1.5px solid #444;
                border-radius: 8px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_frame)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        # Save button
        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setMinimumWidth(100)
        bottom_layout.addWidget(self.btn_save)
        
        parent_layout.addWidget(bottom_frame)
    
    def setup_connections(self):
        """Setup signal connections"""
        # List interactions
        self.actuator_list.itemClicked.connect(self.on_actuator_selected)
        self.actuator_list.itemDoubleClicked.connect(self.edit_actuator)
        self.actuator_list.actuator_renamed.connect(self.rename_actuator)
        self.actuator_list.actuator_deleted.connect(self.delete_actuator)
        
        # Button connections
        self.btn_update_count.clicked.connect(self.update_actuator_count)
        self.btn_add_actuator.clicked.connect(self.add_actuator)
        self.btn_edit_actuator.clicked.connect(self.edit_actuator)
        self.btn_duplicate_actuator.clicked.connect(self.duplicate_actuator)
        
        self.btn_save.clicked.connect(self.save_configuration)
        
        # Preview test buttons
        self.preview_widget.btn_test_on.clicked.connect(lambda: self.test_actuator(True))
        self.preview_widget.btn_test_off.clicked.connect(lambda: self.test_actuator(False))
    
    def update_actuator_count(self):
        """Update the number of actuators"""
        count = self.actuator_count_spin.value()
        self.actuator_list.clear()
        self.actuator_configs.clear()
        
        for i in range(1, count + 1):
            name = f"Actuator {i}"
            config = ActuatorConfig(
                name=name,
                pin=i-1,
                command_template="G55 P{id} S{state};"
            )
            self.actuator_configs[name] = config
            
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.actuator_list.addItem(item)
        
        self.update_status(f"Created {count} actuators")
        self.configuration_changed.emit()
    
    def on_actuator_selected(self, item):
        """Handle actuator selection"""
        name = item.data(Qt.UserRole)
        if name in self.actuator_configs:
            self.preview_widget.update_preview(self.actuator_configs[name])
            self.btn_edit_actuator.setEnabled(True)
            self.btn_duplicate_actuator.setEnabled(True)
        else:
            self.preview_widget.clear_preview()
    
    def add_actuator(self):
        """Add a new actuator"""
        name, ok = QInputDialog.getText(self, "Add Actuator", "Enter actuator name:")
        if ok and name:
            if name in self.actuator_configs:
                QMessageBox.warning(self, "Duplicate Name", "An actuator with this name already exists!")
                return
            
            config = ActuatorConfig(name=name, pin=len(self.actuator_configs))
            self.actuator_configs[name] = config
            
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.actuator_list.addItem(item)
            
            self.actuator_count_spin.setValue(len(self.actuator_configs))
            self.update_status(f"Added actuator: {name}")
            self.configuration_changed.emit()
    
    def edit_actuator(self, item=None):
        """Edit actuator configuration"""
        if item is None:
            item = self.actuator_list.currentItem()
        
        if not item:
            return
        
        name = item.data(Qt.UserRole)
        if name not in self.actuator_configs:
            return
        
        # Make the list item editable
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.actuator_list.editItem(item)
        
        # Store the original name for comparison
        self.editing_original_name = name
        
        # Connect to itemChanged signal to handle the edit
        self.actuator_list.itemChanged.connect(self.on_actuator_item_changed)
        
        # Also open the dialog for full configuration editing
        dialog = ActuatorDialog(
            actuator_name=name,
            config=self.actuator_configs[name]
        )
        
        if dialog.exec():
            new_config = dialog.get_config()
            self.actuator_configs[name] = new_config
            
            # Update item text if name changed
            if new_config.name != name:
                del self.actuator_configs[name]
                self.actuator_configs[new_config.name] = new_config
                item.setText(new_config.name)
                item.setData(Qt.UserRole, new_config.name)
            
            self.preview_widget.update_preview(new_config)
            self.update_status(f"Updated actuator: {new_config.name}")
            self.configuration_changed.emit()
    
    def duplicate_actuator(self):
        """Duplicate the selected actuator"""
        item = self.actuator_list.currentItem()
        if not item:
            return
        
        name = item.data(Qt.UserRole)
        if name not in self.actuator_configs:
            return
        
        new_name = f"{name} (Copy)"
        counter = 1
        while new_name in self.actuator_configs:
            new_name = f"{name} (Copy {counter})"
            counter += 1
        
        # Create duplicate config
        original_config = self.actuator_configs[name]
        new_config = ActuatorConfig(
            name=new_name,
            enabled=original_config.enabled,
            command_template=original_config.command_template,
            description=original_config.description,
            pin=len(self.actuator_configs),
            inverted=original_config.inverted
        )
        
        self.actuator_configs[new_name] = new_config
        
        new_item = QListWidgetItem(new_name)
        new_item.setData(Qt.UserRole, new_name)
        self.actuator_list.addItem(new_item)
        
        self.update_status(f"Duplicated actuator: {new_name}")
        self.configuration_changed.emit()
    
    def rename_actuator(self, old_name: str, new_name: str):
        """Handle actuator rename"""
        if old_name in self.actuator_configs:
            config = self.actuator_configs[old_name]
            config.name = new_name
            del self.actuator_configs[old_name]
            self.actuator_configs[new_name] = config
            self.update_status(f"Renamed actuator: {old_name} → {new_name}")
            self.configuration_changed.emit()
    
    def delete_actuator(self, name: str):
        """Handle actuator deletion"""
        if name in self.actuator_configs:
            del self.actuator_configs[name]
            self.actuator_count_spin.setValue(len(self.actuator_configs))
            self.preview_widget.clear_preview()
            self.update_status(f"Deleted actuator: {name}")
            self.configuration_changed.emit()
    
    def test_actuator(self, state: bool):
        """Test actuator command"""
        if not self.preview_widget.current_config:
            return
        
        # Use custom commands from input fields if available
        if state:
            command = self.preview_widget.on_command_input.text().strip()
            if not command:
                # Fallback to generated command
                config = self.preview_widget.current_config
                command = self.preview_widget.generate_example_command(config, True)
        else:
            command = self.preview_widget.off_command_input.text().strip()
            if not command:
                # Fallback to generated command
                config = self.preview_widget.current_config
                command = self.preview_widget.generate_example_command(config, False)
        
        self.actuator_command_sent.emit(command)
        self.update_status(f"Sent: {command}")
    
    def update_status(self, message: str):
        """Update status label"""
        self.status_label.setText(message)
    
    def apply_styles(self):
        """Apply custom styles to match global dark theme"""
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
            
            QPushButton {
                background-color: #1976d2;
                border: none;
                border-radius: 8px;
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
            
            QListWidget {
                border: 1.5px solid #444;
                border-radius: 6px;
                background-color: #232629;
                alternate-background-color: #282c34;
                color: #f0f0f0;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #444;
            }
            
            QListWidget::item:selected {
                background-color: #1976d2;
                color: white;
            }
            
            QListWidget::item:hover {
                background-color: #2c3e50;
            }
            
            QFrame {
                background-color: #232629;
                border: 1px solid #444;
                border-radius: 8px;
                color: #f0f0f0;
            }
            
            QTextEdit {
                border: 1.5px solid #444;
                border-radius: 6px;
                background-color: #232629;
                color: #f0f0f0;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            
            QSpinBox {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 4px 8px;
            }
            
            QComboBox {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 4px 8px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #f0f0f0;
            }
            
            QLabel {
                color: #f0f0f0;
            }
        """)
    
    def get_actuator_configs(self) -> Dict[str, ActuatorConfig]:
        """Get all actuator configurations"""
        return self.actuator_configs.copy()
    
    def set_actuator_configs(self, configs: Dict[str, ActuatorConfig]):
        """Set actuator configurations"""
        self.actuator_configs = configs.copy()
        self.refresh_actuator_list()
    
    def refresh_actuator_list(self):
        """Refresh the actuator list display"""
        self.actuator_list.clear()
        for name, config in self.actuator_configs.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            if not config.enabled:
                item.setForeground(Qt.gray)
            self.actuator_list.addItem(item)
        
        self.actuator_count_spin.setValue(len(self.actuator_configs))
    
    def on_actuator_item_changed(self, item):
        """Handle when an actuator list item is changed (inline editing)"""
        if not hasattr(self, 'editing_original_name'):
            return
        
        new_name = item.text().strip()
        old_name = self.editing_original_name
        
        if not new_name:
            # If empty, revert to original name
            item.setText(old_name)
            return
        
        if new_name == old_name:
            # No change, just clean up
            self.cleanup_editing()
            return
        
        # Check if new name already exists
        if new_name in self.actuator_configs and new_name != old_name:
            QMessageBox.warning(self, "Duplicate Name", "An actuator with this name already exists!")
            item.setText(old_name)
            self.cleanup_editing()
            return
        
        # Update the configuration
        if old_name in self.actuator_configs:
            config = self.actuator_configs[old_name]
            config.name = new_name
            del self.actuator_configs[old_name]
            self.actuator_configs[new_name] = config
            item.setData(Qt.UserRole, new_name)
            
            self.update_status(f"Renamed actuator: {old_name} → {new_name}")
            self.configuration_changed.emit()
        
        self.cleanup_editing()
    
    def cleanup_editing(self):
        """Clean up editing state"""
        if hasattr(self, 'editing_original_name'):
            delattr(self, 'editing_original_name')
        # Disconnect the signal to avoid multiple connections
        try:
            self.actuator_list.itemChanged.disconnect(self.on_actuator_item_changed)
        except:
            pass

    def save_configuration(self):
        """Save actuator configuration using ConfigManager"""
        try:
            self.config_manager.set_actuator_configs(self.actuator_configs)
            self.update_status("Configuration saved successfully")
            QMessageBox.information(self, "Saved", "Actuator configuration saved successfully!")
        except Exception as e:
            self.update_status(f"Save failed: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{str(e)}")

    def load_configuration(self):
        """Load actuator configuration using ConfigManager"""
        try:
            self.actuator_configs = self.config_manager.get_actuator_configs()
            self.refresh_actuator_list()
            self.update_status("Configuration loaded successfully")
        except Exception as e:
            self.update_status(f"Load failed: {str(e)}")
            self.update_actuator_count()  # fallback