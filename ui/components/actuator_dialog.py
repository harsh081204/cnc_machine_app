from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QLineEdit, QSpinBox, QCheckBox, QTextEdit, QPushButton,
    QDialogButtonBox, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActuatorConfig:
    """Configuration data for an actuator"""
    name: str
    enabled: bool = True
    command_template: str = "G55 P{id} S{state};"
    description: str = ""
    pin: int = 0
    inverted: bool = False


class ActuatorDialog(QDialog):
    """Dialog for editing actuator configuration"""
    
    def __init__(self, actuator_name: str, config: ActuatorConfig, parent=None):
        super().__init__(parent)
        self.actuator_name = actuator_name
        self.original_config = config
        self.setWindowTitle(f"Edit Actuator: {actuator_name}")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.init_ui()
        self.load_config(config)
        self.setup_connections()
        self.apply_styles()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Basic settings group
        basic_group = self.create_basic_group()
        layout.addWidget(basic_group)
        
        # Command settings group
        command_group = self.create_command_group()
        layout.addWidget(command_group)
        
        # Description group
        desc_group = self.create_description_group()
        layout.addWidget(desc_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        layout.addWidget(button_box)
        
        # Connect buttons
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
    
    def create_basic_group(self):
        """Create basic settings group"""
        group = QGroupBox("Basic Settings")
        layout = QFormLayout(group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter actuator name")
        
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        
        self.pin_spin = QSpinBox()
        self.pin_spin.setRange(0, 255)
        self.pin_spin.setToolTip("Pin number for this actuator")
        
        self.inverted_check = QCheckBox("Inverted logic")
        self.inverted_check.setToolTip("Invert the ON/OFF logic")
        
        layout.addRow("Name:", self.name_edit)
        layout.addRow("", self.enabled_check)
        layout.addRow("Pin:", self.pin_spin)
        layout.addRow("", self.inverted_check)
        
        return group
    
    def create_command_group(self):
        """Create command template group"""
        group = QGroupBox("Command Template")
        layout = QVBoxLayout(group)
        
        # Template input
        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText("G55 P{id} S{state};")
        self.template_edit.setToolTip(
            "Use {id} for pin number, {state} for state (0/1), {name} for actuator name"
        )
        
        # Template help
        help_label = QLabel(
            "Available placeholders:\n"
            "• {id} - Pin number\n"
            "• {state} - State (0=OFF, 1=ON)\n"
            "• {name} - Actuator name\n"
            "• {true:255} - Value when ON\n"
            "• {false:0} - Value when OFF"
        )
        help_label.setStyleSheet("color: #b0b0b0; font-size: 10px;")
        
        layout.addWidget(self.template_edit)
        layout.addWidget(help_label)
        
        return group
    
    def create_description_group(self):
        """Create description group"""
        group = QGroupBox("Description")
        layout = QVBoxLayout(group)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("Optional description for this actuator")
        
        layout.addWidget(self.desc_edit)
        
        return group
    
    def setup_connections(self):
        """Setup signal connections"""
        self.name_edit.textChanged.connect(self.validate_inputs)
        self.template_edit.textChanged.connect(self.validate_inputs)
    
    def load_config(self, config: ActuatorConfig):
        """Load configuration into the dialog"""
        self.name_edit.setText(config.name)
        self.enabled_check.setChecked(config.enabled)
        self.pin_spin.setValue(config.pin)
        self.inverted_check.setChecked(config.inverted)
        self.template_edit.setText(config.command_template)
        self.desc_edit.setPlainText(config.description)
    
    def validate_inputs(self):
        """Validate user inputs"""
        name = self.name_edit.text().strip()
        template = self.template_edit.text().strip()
        
        # Basic validation
        if not name:
            self.name_edit.setStyleSheet("border: 2px solid #e74c3c; background-color: #232629; color: #f0f0f0;")
        else:
            self.name_edit.setStyleSheet("border: 1.5px solid #444; background-color: #232629; color: #f0f0f0;")
        
        if not template:
            self.template_edit.setStyleSheet("border: 2px solid #e74c3c; background-color: #232629; color: #f0f0f0;")
        else:
            self.template_edit.setStyleSheet("border: 1.5px solid #444; background-color: #232629; color: #f0f0f0;")
    
    def get_config(self) -> ActuatorConfig:
        """Get the current configuration from the dialog"""
        return ActuatorConfig(
            name=self.name_edit.text().strip(),
            enabled=self.enabled_check.isChecked(),
            command_template=self.template_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            pin=self.pin_spin.value(),
            inverted=self.inverted_check.isChecked()
        )
    
    def accept(self):
        """Handle dialog acceptance with validation"""
        config = self.get_config()
        
        # Validate required fields
        if not config.name:
            QMessageBox.warning(self, "Validation Error", "Actuator name is required!")
            return
        
        if not config.command_template:
            QMessageBox.warning(self, "Validation Error", "Command template is required!")
            return
        
        super().accept()

    def apply_styles(self):
        """Apply dark theme styling to match global design"""
        self.setStyleSheet("""
            QDialog {
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
            
            QLineEdit, QTextEdit {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 6px 8px;
            }
            
            QLineEdit:focus, QTextEdit:focus {
                border-color: #1976d2;
            }
            
            QSpinBox {
                border: 1.5px solid #444;
                border-radius: 4px;
                background-color: #232629;
                color: #f0f0f0;
                padding: 4px 8px;
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
                font-size: 12px;
            }
            
            QLabel {
                color: #f0f0f0;
            }
            
            QDialogButtonBox QPushButton {
                background-color: #1976d2;
                border: none;
                border-radius: 6px;
                color: #f0f0f0;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }
            
            QDialogButtonBox QPushButton:hover {
                background-color: #1565c0;
            }
            
            QDialogButtonBox QPushButton:pressed {
                background-color: #115293;
            }
            
            QDialogButtonBox QPushButton[text="Cancel"] {
                background-color: #666;
            }
            
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                background-color: #555;
            }
        """)
