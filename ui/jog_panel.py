# ui/jog_panel.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGridLayout, QSizePolicy, QComboBox, QFrame, QSpacerItem, QSlider, QLineEdit
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, Signal, QSize
from enum import Enum
from core.config_manager import JogConfig
from PySide6.QtGui import QDoubleValidator


class JogDirection(Enum):
    """Enumeration for jog directions"""
    X_POSITIVE = "X+"
    X_NEGATIVE = "X-"
    Y_POSITIVE = "Y+"
    Y_NEGATIVE = "Y-"
    Z_POSITIVE = "Z+"
    Z_NEGATIVE = "Z-"


class JogPanel(QWidget):
    """Enhanced Jog Control Panel with improved styling and functionality"""
    
    # Signals for communication with parent/controller
    jog_requested = Signal(str, float, int)  # direction, distance, speed
    home_requested = Signal()
    park_requested = Signal()
    start_requested = Signal()
    emergency_stop_requested = Signal()
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.jog_distances = [0.1, 0.5, 1.0, 5.0, 10.0]  # default
        self.current_jog_distance = 1.0
        self.current_jog_speed = 1000  # mm/min default
        self.init_ui()
        self.setup_connections()
        self.apply_styles()
        self.load_jog_config()
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Title section
        self.create_title_section(main_layout)
        
        # Control buttons section
        self.create_control_section(main_layout)
        
        # Jog distance input section
        self.create_distance_section(main_layout)
        
        # Movement controls section
        self.create_movement_section(main_layout)
        
        # Emergency stop
        self.create_emergency_section(main_layout)
    
    def create_title_section(self, parent_layout):
        """Create the title section"""
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("🎮 Jog Controls")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #f0f0f0; padding: 8px 0;")
        title_layout.addWidget(title)
        
        parent_layout.addLayout(title_layout)
    
    def create_control_section(self, parent_layout):
        """Create the main control buttons section"""
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # Control buttons
        self.btn_start = QPushButton("▶ Start")
        self.btn_home = QPushButton("⌂ Home")
        self.btn_park = QPushButton("⏹ Park")
        
        control_buttons = [self.btn_start, self.btn_home, self.btn_park]
        
        for btn in control_buttons:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            btn.setMinimumHeight(36)
            btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
            control_layout.addWidget(btn)
        
        parent_layout.addLayout(control_layout)
    
    def create_distance_section(self, parent_layout):
        """Create jog distance input section (only distance, no speed slider here)"""
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(10)

        distance_label = QLabel("Distance:")
        distance_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        distance_label.setStyleSheet("color: #f0f0f0;")
        self.distance_edit = QLineEdit(str(self.current_jog_distance))
        self.distance_edit.setFixedWidth(80)
        self.distance_edit.setPlaceholderText("mm")
        self.distance_edit.setValidator(QDoubleValidator(0.01, 1000.0, 3))
        self.distance_edit.setToolTip("Enter jog distance in mm")

        section_layout.addWidget(distance_label)
        section_layout.addWidget(self.distance_edit)
        section_layout.addStretch()
        parent_layout.addLayout(section_layout)
    
    def create_movement_section(self, parent_layout):
        """Create the movement controls section with grid layout for jog buttons and adjacent speed slider"""
        movement_layout = QHBoxLayout()
        movement_layout.setSpacing(32)
        movement_layout.setContentsMargins(0, 0, 0, 0)

        # Jog grid (X/Y/Z)
        jog_grid = QGridLayout()
        jog_grid.setSpacing(8)

        # X/Y buttons in cross
        self.btn_y_pos = QPushButton("↑")
        self.btn_y_pos.setFixedSize(48, 48)
        self.btn_y_pos.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_y_pos.setToolTip("Jog +Y")
        jog_grid.addWidget(self.btn_y_pos, 0, 1)

        self.btn_x_neg = QPushButton("←")
        self.btn_x_neg.setFixedSize(48, 48)
        self.btn_x_neg.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_x_neg.setToolTip("Jog -X")
        jog_grid.addWidget(self.btn_x_neg, 1, 0)

        self.btn_xy_home = QPushButton("⌂")
        self.btn_xy_home.setFixedSize(48, 48)
        self.btn_xy_home.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_xy_home.setToolTip("Move XY to home position")
        jog_grid.addWidget(self.btn_xy_home, 1, 1)

        self.btn_x_pos = QPushButton("→")
        self.btn_x_pos.setFixedSize(48, 48)
        self.btn_x_pos.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_x_pos.setToolTip("Jog +X")
        jog_grid.addWidget(self.btn_x_pos, 1, 2)

        self.btn_y_neg = QPushButton("↓")
        self.btn_y_neg.setFixedSize(48, 48)
        self.btn_y_neg.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.btn_y_neg.setToolTip("Jog -Y")
        jog_grid.addWidget(self.btn_y_neg, 2, 1)

        # Z+ and Z- vertically to the right
        z_layout = QVBoxLayout()
        z_layout.setSpacing(8)
        self.btn_z_pos = QPushButton("Z+")
        self.btn_z_pos.setFixedSize(48, 40)
        self.btn_z_pos.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_z_pos.setToolTip("Jog +Z")
        z_layout.addWidget(self.btn_z_pos)
        self.btn_z_home = QPushButton("Z⌂")
        self.btn_z_home.setFixedSize(48, 32)
        self.btn_z_home.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_z_home.setToolTip("Move Z to home position")
        z_layout.addWidget(self.btn_z_home)
        self.btn_z_neg = QPushButton("Z-")
        self.btn_z_neg.setFixedSize(48, 40)
        self.btn_z_neg.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_z_neg.setToolTip("Jog -Z")
        z_layout.addWidget(self.btn_z_neg)
        jog_grid.addLayout(z_layout, 0, 3, 3, 1)

        # Add jog grid to movement layout
        movement_layout.addLayout(jog_grid)

        # Speed slider (vertical, right of jog grid)
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(8)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_label = QLabel("Speed (%)")
        speed_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        speed_label.setStyleSheet("color: #f0f0f0;")
        self.speed_slider = QSlider(Qt.Vertical)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(self.speed_to_percent(self.current_jog_speed))
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.setFixedHeight(120)
        self.speed_value_label = QLabel(self.get_speed_label(self.current_jog_speed))
        self.speed_value_label.setFont(QFont("Segoe UI", 9))
        self.speed_value_label.setStyleSheet("color: #f0f0f0;")
        speed_layout.addWidget(speed_label, alignment=Qt.AlignHCenter)
        speed_layout.addWidget(self.speed_slider, alignment=Qt.AlignHCenter)
        speed_layout.addWidget(self.speed_value_label, alignment=Qt.AlignHCenter)
        movement_layout.addSpacing(24)
        movement_layout.addLayout(speed_layout)

        parent_layout.addLayout(movement_layout)
    
    def create_emergency_section(self, parent_layout):
        """Create emergency stop section"""
        emergency_layout = QHBoxLayout()
        
        # Spacer
        emergency_layout.addStretch()
        
        # Emergency stop button
        self.btn_emergency = QPushButton("🛑 EMERGENCY STOP")
        self.btn_emergency.setMinimumHeight(50)
        self.btn_emergency.setMinimumWidth(200)
        self.btn_emergency.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        emergency_layout.addWidget(self.btn_emergency)
        emergency_layout.addStretch()
        
        parent_layout.addLayout(emergency_layout)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Control buttons
        self.btn_start.clicked.connect(self.start_requested.emit)
        self.btn_home.clicked.connect(self.home_requested.emit)
        self.btn_park.clicked.connect(self.park_requested.emit)
        
        # Movement buttons
        self.btn_x_pos.clicked.connect(lambda: self.handle_jog(JogDirection.X_POSITIVE))
        self.btn_x_neg.clicked.connect(lambda: self.handle_jog(JogDirection.X_NEGATIVE))
        self.btn_y_pos.clicked.connect(lambda: self.handle_jog(JogDirection.Y_POSITIVE))
        self.btn_y_neg.clicked.connect(lambda: self.handle_jog(JogDirection.Y_NEGATIVE))
        self.btn_z_pos.clicked.connect(lambda: self.handle_jog(JogDirection.Z_POSITIVE))
        self.btn_z_neg.clicked.connect(lambda: self.handle_jog(JogDirection.Z_NEGATIVE))
        
        # Home buttons
        self.btn_xy_home.clicked.connect(lambda: self.jog_requested.emit("XY_HOME", 0, 0))
        self.btn_z_home.clicked.connect(lambda: self.jog_requested.emit("Z_HOME", 0, 0))
        
        # Distance input
        self.distance_edit.editingFinished.connect(self.update_jog_distance)
        # Speed slider
        self.speed_slider.valueChanged.connect(self.update_jog_speed)
        
        # Emergency stop
        self.btn_emergency.clicked.connect(self.emergency_stop_requested.emit)
    
    def handle_jog(self, direction: JogDirection):
        # Validate distance
        try:
            distance = float(self.distance_edit.text())
            if distance <= 0:
                return
        except ValueError:
            return
        self.jog_requested.emit(direction.value, distance, self.current_jog_speed)
    
    def update_jog_distance(self):
        try:
            value = float(self.distance_edit.text())
            self.current_jog_distance = value
        except ValueError:
            pass
    
    def update_jog_speed(self, percent: int):
        self.current_jog_speed = self.percent_to_speed(percent)
        self.speed_value_label.setText(self.get_speed_label(self.current_jog_speed))
    
    def speed_to_percent(self, speed):
        # Map speed (100-10000) to percent (0-100)
        return int((speed - 100) / (10000 - 100) * 100)

    def percent_to_speed(self, percent):
        # Map percent (0-100) to speed (100-10000)
        return int(100 + (percent / 100) * (10000 - 100))

    def get_speed_label(self, speed):
        percent = self.speed_to_percent(speed)
        return f"{percent}% ({speed} mm/min)"
    
    def apply_styles(self):
        """Apply custom styles to the panel for dark mode consistency"""
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
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
            
            QPushButton {
                background-color: #1976d2;
                border: none;
                border-radius: 6px;
                color: #f0f0f0;
                font-weight: bold;
                padding: 8px 12px;
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
            
            QPushButton#emergency {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            
            QPushButton#emergency:hover {
                background-color: #c0392b;
            }
            
            QPushButton#emergency:pressed {
                background-color: #a93226;
            }
            
            QPushButton#movement {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            
            QPushButton#movement:hover {
                background-color: #34495e;
                border-color: #1976d2;
            }
            
            QPushButton#movement:pressed {
                background-color: #2c3e50;
                border-color: #1565c0;
            }
            
            QPushButton#home {
                background-color: #27ae60;
                border: 2px solid #27ae60;
            }
            
            QPushButton#home:hover {
                background-color: #229954;
                border-color: #229954;
            }
            
            QPushButton#control {
                background-color: #3498db;
                border: 2px solid #3498db;
                font-size: 11px;
            }
            
            QPushButton#control:hover {
                background-color: #2980b9;
                border-color: #2980b9;
            }
        """)
        # Set object names for specific styling
        self.btn_emergency.setObjectName("emergency")
        
        # Set movement button object names
        for btn in [self.btn_x_pos, self.btn_x_neg, self.btn_y_pos, self.btn_y_neg, self.btn_z_pos, self.btn_z_neg]:
            btn.setObjectName("movement")
        
        # Set home button object names
        for btn in [self.btn_xy_home, self.btn_z_home]:
            btn.setObjectName("home")
        
        # Set control button object names
        for btn in [self.btn_start, self.btn_home, self.btn_park]:
            btn.setObjectName("control")
    
    def set_enabled_state(self, enabled: bool):
        """Enable/disable all controls"""
        for widget in self.findChildren(QPushButton):
            if widget != self.btn_emergency:  # Emergency stop should always be enabled
                widget.setEnabled(enabled)
        self.distance_edit.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)
    
    def get_current_jog_distance(self) -> float:
        """Get the current jog distance"""
        return self.current_jog_distance
    
    def load_jog_config(self):
        config = self.config_manager.get_jog_config()
        if config.step_sizes:
            self.jog_distances = config.step_sizes
            self.distance_edit.setText(str(self.current_jog_distance))
            self.current_jog_distance = self.jog_distances[0]
            self.speed_slider.setValue(self.speed_to_percent(self.current_jog_speed))
            self.current_jog_speed = self.jog_distances[0]