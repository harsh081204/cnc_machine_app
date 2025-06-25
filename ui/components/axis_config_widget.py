# ui/components/axis_config_widget.py
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QGroupBox, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QFrame, QToolTip, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QDoubleValidator, QFont, QPalette, QColor
import logging
from typing import Dict, Any, Optional

class AxisConfigWidget(QGroupBox):
    # Signals for parent communication
    config_changed = Signal()           # Emitted when any value changes
    validation_error = Signal(str)      # Emitted when validation fails
    field_focused = Signal(str, str)    # Emitted when field gets focus (axis, field)
    
    def __init__(self, axis_name: str = "Axis", color: str = "#4ECDC4", parent=None):
        super().__init__(axis_name, parent)
        self.axis_name = axis_name
        self.color = color
        self.logger = logging.getLogger(__name__)
        self.is_valid = True
        self.field_values = {}
        self.init_ui()
        self.connect_signals()
        self.setup_validation()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Unified border color for all axes
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid #2986cc;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: rgba({self._hex_to_rgb(self.color)}, 0.05);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2986cc;
                font-size: 12px;
            }}
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        
        # Create form with enhanced input fields
        form_widget = self.create_form_section()
        main_layout.addWidget(form_widget)
        
        # Add status and controls section
        controls_widget = self.create_controls_section()
        main_layout.addWidget(controls_widget)
        
        self.setLayout(main_layout)
    
    def create_form_section(self):
        """Create the main form section with input fields"""
        widget = QWidget()
        form_layout = QFormLayout(widget)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setSpacing(12)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Enhanced validators with specific ranges for each field type
        position_validator = QDoubleValidator(-9999.0, 9999.0, 3)
        positive_validator = QDoubleValidator(0.0, 99999.0, 3)
        
        # Create enhanced input fields with units and validation
        self.min_input = self.create_enhanced_input("Min Position", "mm", -1000.0, 1000.0, position_validator)
        self.max_input = self.create_enhanced_input("Max Position", "mm", -1000.0, 1000.0, position_validator)
        self.acc_input = self.create_enhanced_input("Acceleration", "mm/s²", 0.1, 10000.0, positive_validator)
        self.feedrate_input = self.create_enhanced_input("Feedrate", "mm/min", 1.0, 50000.0, positive_validator)
        self.jerk_input = self.create_enhanced_input("Jerk", "mm/s³", 0.1, 1000.0, positive_validator)
        
        # Add rows to form with enhanced labels
        form_layout.addRow(self.create_field_label("📏 Min Position:", "Minimum travel position"), self.min_input['widget'])
        form_layout.addRow(self.create_field_label("📏 Max Position:", "Maximum travel position"), self.max_input['widget'])
        form_layout.addRow(self.create_field_label("⚡ Acceleration:", "Maximum acceleration rate"), self.acc_input['widget'])
        form_layout.addRow(self.create_field_label("🏃 Feedrate:", "Maximum feed rate"), self.feedrate_input['widget'])
        form_layout.addRow(self.create_field_label("💨 Jerk:", "Maximum jerk (acceleration change rate)"), self.jerk_input['widget'])
        
        return widget
    
    def create_enhanced_input(self, field_name: str, unit: str, min_val: float, max_val: float, validator):
        """Create an enhanced input field with unit display and validation"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Main input field
        input_field = QLineEdit()
        input_field.setValidator(validator)
        input_field.setPlaceholderText(f"{min_val} - {max_val}")
        input_field.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid #2986cc;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
                background-color: transparent;
            }}
            QLineEdit:focus {{
                border-color: {self.color};
                background-color: #232629;
            }}
            QLineEdit[validation-error="true"] {{
                border-color: #e74c3c;
                background-color: #2a2323;
            }}
            QLineEdit[validation-success="true"] {{
                border-color: #27ae60;
                background-color: #23292a;
            }}
        """)
        
        # Unit label
        unit_label = QLabel(unit)
        unit_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-size: 10px;
                font-weight: bold;
                padding: 2px 4px;
                background-color: rgba({self._hex_to_rgb(self.color)}, 0.15);
                border-radius: 3px;
            }}
        """)
        unit_label.setMinimumWidth(50)
        unit_label.setAlignment(Qt.AlignCenter)
        
        # Status indicator
        status_label = QLabel("●")
        status_label.setStyleSheet("color: #bdc3c7; font-size: 8px;")
        status_label.setFixedWidth(12)
        status_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(input_field)
        layout.addWidget(unit_label)
        layout.addWidget(status_label)
        
        return {
            'widget': container,
            'input': input_field,
            'unit': unit_label,
            'status': status_label,
            'field_name': field_name,
            'min_val': min_val,
            'max_val': max_val
        }
    
    def create_field_label(self, text: str, tooltip: str):
        """Create an enhanced field label with tooltip"""
        label = QLabel(text)
        label.setToolTip(tooltip)
        label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #f0f0f0;
                font-size: 11px;
            }
        """)
        return label
    
    def create_controls_section(self):
        """Create controls and status section"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({self._hex_to_rgb(self.color)}, 0.10);
                border-radius: 4px;
                border: 1px solid rgba({self._hex_to_rgb(self.color)}, 0.3);
            }}
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        
        # Status indicator
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color: #27ae60; font-size: 10px; font-weight: bold;")
        
        # Quick action buttons
        self.btn_preset_slow = QPushButton("Slow")
        self.btn_preset_fast = QPushButton("Fast")
        self.btn_clear = QPushButton("Clear")
        
        button_style = f"""
            QPushButton {{
                padding: 4px 8px;
                border: 1px solid {self.color};
                border-radius: 3px;
                background-color: #232629;
                font-size: 10px;
                font-weight: bold;
                color: {self.color};
            }}
            QPushButton:hover {{
                background-color: rgba({self._hex_to_rgb(self.color)}, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba({self._hex_to_rgb(self.color)}, 0.3);
            }}
        """
        
        for btn in [self.btn_preset_slow, self.btn_preset_fast, self.btn_clear]:
            btn.setStyleSheet(button_style)
            btn.setMaximumHeight(24)
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(QLabel("Presets:"))
        layout.addWidget(self.btn_preset_slow)
        layout.addWidget(self.btn_preset_fast)
        layout.addWidget(self.btn_clear)
        
        return widget
    
    def connect_signals(self):
        """Connect all widget signals"""
        # Input field connections
        fields = [self.min_input, self.max_input, self.acc_input, self.feedrate_input, self.jerk_input]
        
        for field_info in fields:
            input_field = field_info['input']
            input_field.textChanged.connect(self.on_value_changed)
            input_field.editingFinished.connect(self.validate_field)
            input_field.installEventFilter(self)
        
        # Button connections
        self.btn_preset_slow.clicked.connect(self.apply_slow_preset)
        self.btn_preset_fast.clicked.connect(self.apply_fast_preset)
        self.btn_clear.clicked.connect(self.clear_fields)
    
    def setup_validation(self):
        """Setup validation rules and constraints"""
        self.validation_rules = {
            'min_max_check': "Min position must be less than max position",
            'positive_values': "Acceleration, feedrate, and jerk must be positive",
            'reasonable_ranges': "Values should be within reasonable ranges for CNC operation"
        }
    
    def on_value_changed(self):
        """Handle when any input value changes"""
        self.config_changed.emit()
        
        # Delayed validation to avoid excessive validation during typing
        if hasattr(self, '_validation_timer'):
            self._validation_timer.stop()
        
        self._validation_timer = QTimer()
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self.validate_all_fields)
        self._validation_timer.start(500)  # Validate after 500ms of no changes
    
    def validate_field(self):
        """Validate individual field"""
        sender = self.sender()
        field_info = self.get_field_info_by_input(sender)
        
        if field_info:
            is_valid = self.validate_single_field(field_info)
            self.update_field_visual_state(field_info, is_valid)
    
    def validate_single_field(self, field_info) -> bool:
        """Validate a single field and return result"""
        try:
            text = field_info['input'].text().strip()
            if not text:
                return True  # Empty is valid (will use defaults)
            
            value = float(text)
            min_val = field_info['min_val']
            max_val = field_info['max_val']
            
            if not (min_val <= value <= max_val):
                field_info['status'].setStyleSheet("color: #e74c3c; font-size: 8px;")
                field_info['status'].setText("⚠")
                field_info['status'].setToolTip(f"Value must be between {min_val} and {max_val}")
                return False
            
            field_info['status'].setStyleSheet("color: #27ae60; font-size: 8px;")
            field_info['status'].setText("✓")
            field_info['status'].setToolTip("Valid value")
            return True
            
        except ValueError:
            field_info['status'].setStyleSheet("color: #e74c3c; font-size: 8px;")
            field_info['status'].setText("✗")
            field_info['status'].setToolTip("Invalid number format")
            return False
    
    def validate_all_fields(self) -> bool:
        """Validate all fields and cross-field constraints"""
        fields = [self.min_input, self.max_input, self.acc_input, self.feedrate_input, self.jerk_input]
        all_valid = True
        
        # Validate individual fields
        for field_info in fields:
            if not self.validate_single_field(field_info):
                all_valid = False
        
        # Cross-field validation
        try:
            min_val = float(self.min_input['input'].text() or "0")
            max_val = float(self.max_input['input'].text() or "100")
            
            if min_val >= max_val:
                self.set_status("⚠️ Min must be less than Max", "error")
                self.validation_error.emit("Min position must be less than max position")
                all_valid = False
        except ValueError:
            pass  # Individual field validation will catch this
        
        # Update overall status
        if all_valid:
            self.set_status("✅ Valid configuration", "success")
            self.is_valid = True
        else:
            self.is_valid = False
        
        return all_valid
    
    def validate(self) -> bool:
        """Public method to validate this widget"""
        return self.validate_all_fields()
    
    def update_field_visual_state(self, field_info, is_valid: bool):
        """Update visual state of a field based on validation"""
        input_field = field_info['input']
        
        if is_valid:
            input_field.setProperty("validation-error", "false")
            input_field.setProperty("validation-success", "true")
        else:
            input_field.setProperty("validation-error", "true")
            input_field.setProperty("validation-success", "false")
        
        input_field.style().polish(input_field)
    
    def set_status(self, message: str, status_type: str = "info"):
        """Set status message with appropriate styling"""
        colors = {
            "success": "#27ae60",
            "error": "#e74c3c",
            "warning": "#f39c12",
            "info": "#3498db"
        }
        
        color = colors.get(status_type, colors["info"])
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
    
    def get_field_info_by_input(self, input_widget):
        """Get field info dictionary by input widget"""
        fields = [self.min_input, self.max_input, self.acc_input, self.feedrate_input, self.jerk_input]
        for field_info in fields:
            if field_info['input'] == input_widget:
                return field_info
        return None
    
    def apply_slow_preset(self):
        """Apply slow/precise movement preset"""
        presets = {
            'X Axis': {'acc': '800', 'feedrate': '1000', 'jerk': '8'},
            'Y Axis': {'acc': '800', 'feedrate': '1000', 'jerk': '8'},
            'Z Axis': {'acc': '400', 'feedrate': '500', 'jerk': '5'}
        }
        
        preset = presets.get(self.axis_name, presets['X Axis'])
        self.acc_input['input'].setText(preset['acc'])
        self.feedrate_input['input'].setText(preset['feedrate'])
        self.jerk_input['input'].setText(preset['jerk'])
        
        self.set_status("Applied slow preset", "info")
    
    def apply_fast_preset(self):
        """Apply fast movement preset"""
        presets = {
            'X Axis': {'acc': '2000', 'feedrate': '3000', 'jerk': '20'},
            'Y Axis': {'acc': '2000', 'feedrate': '3000', 'jerk': '20'},
            'Z Axis': {'acc': '1000', 'feedrate': '1500', 'jerk': '15'}
        }
        
        preset = presets.get(self.axis_name, presets['X Axis'])
        self.acc_input['input'].setText(preset['acc'])
        self.feedrate_input['input'].setText(preset['feedrate'])
        self.jerk_input['input'].setText(preset['jerk'])
        
        self.set_status("Applied fast preset", "info")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary"""
        try:
            return {
                "min": float(self.min_input['input'].text() or "0"),
                "max": float(self.max_input['input'].text() or "100"),
                "acceleration": float(self.acc_input['input'].text() or "1000"),
                "feedrate": float(self.feedrate_input['input'].text() or "500"),
                "jerk": float(self.jerk_input['input'].text() or "10"),
                "is_valid": self.is_valid,
                "axis_name": self.axis_name
            }
        except ValueError as e:
            self.logger.error(f"Error getting config for {self.axis_name}: {e}")
            return {}
    
    def set_config(self, config: Dict[str, Any]):
        """Set configuration from dictionary"""
        try:
            self.min_input['input'].setText(str(config.get("min", "")))
            self.max_input['input'].setText(str(config.get("max", "")))
            self.acc_input['input'].setText(str(config.get("acceleration", "")))
            self.feedrate_input['input'].setText(str(config.get("feedrate", "")))
            self.jerk_input['input'].setText(str(config.get("jerk", "")))
            
            # Validate after setting values
            QTimer.singleShot(100, self.validate_all_fields)
            
        except Exception as e:
            self.logger.error(f"Error setting config for {self.axis_name}: {e}")
    
    def clear_fields(self):
        """Clear all input fields"""
        fields = [self.min_input, self.max_input, self.acc_input, self.feedrate_input, self.jerk_input]
        
        for field_info in fields:
            field_info['input'].clear()
            field_info['status'].setText("●")
            field_info['status'].setStyleSheet("color: #bdc3c7; font-size: 8px;")
            field_info['input'].setProperty("validation-error", "false")
            field_info['input'].setProperty("validation-success", "false")
            field_info['input'].style().polish(field_info['input'])
        
        self.set_status("Fields cleared", "info")
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB string"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"
    
    # Legacy method compatibility
    def get_values(self) -> dict:
        """Legacy method - use get_config() instead"""
        config = self.get_config()
        return {
            "min": str(config.get("min", "")),
            "max": str(config.get("max", "")),
            "acceleration": str(config.get("acceleration", "")),
            "feedrate": str(config.get("feedrate", "")),
            "jerk": str(config.get("jerk", ""))
        }
    
    def set_values(self, values: dict):
        """Legacy method - use set_config() instead"""
        try:
            config = {
                "min": float(values.get("min", 0)) if values.get("min") else 0,
                "max": float(values.get("max", 100)) if values.get("max") else 100,
                "acceleration": float(values.get("acceleration", 1000)) if values.get("acceleration") else 1000,
                "feedrate": float(values.get("feedrate", 500)) if values.get("feedrate") else 500,
                "jerk": float(values.get("jerk", 10)) if values.get("jerk") else 10
            }
            self.set_config(config)
        except ValueError:
            # If conversion fails, set as strings
            self.min_input['input'].setText(str(values.get("min", "")))
            self.max_input['input'].setText(str(values.get("max", "")))
            self.acc_input['input'].setText(str(values.get("acceleration", "")))
            self.feedrate_input['input'].setText(str(values.get("feedrate", "")))
            self.jerk_input['input'].setText(str(values.get("jerk", "")))
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            for field_info in [self.min_input, self.max_input, self.acc_input, self.feedrate_input, self.jerk_input]:
                if obj is field_info['input']:
                    self.field_focused.emit(self.axis_name, field_info['field_name'])
                    break
        return super().eventFilter(obj, event)