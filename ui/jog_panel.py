# ui/jog_panel.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGridLayout, QSizePolicy, QComboBox, QFrame, QSpacerItem
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, Signal, QSize
from enum import Enum
from core.config_manager import JogConfig


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
    jog_requested = Signal(str, float)  # direction, distance
    home_requested = Signal()
    park_requested = Signal()
    start_requested = Signal()
    emergency_stop_requested = Signal()
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.jog_distances = [0.1, 0.5, 1.0, 5.0, 10.0]  # default
        self.current_jog_distance = 1.0
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
        
        # Jog distance selection
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
        """Create jog distance selection section"""
        distance_layout = QHBoxLayout()
        distance_layout.setContentsMargins(0, 0, 0, 0)
        distance_layout.setSpacing(10)
        
        distance_label = QLabel("Distance:")
        distance_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        distance_label.setStyleSheet("color: #f0f0f0;")
        
        self.distance_combo = QComboBox()
        self.distance_combo.addItems([f"{d} mm" for d in self.jog_distances])
        self.distance_combo.setCurrentText("1.0 mm")
        self.distance_combo.setMinimumWidth(100)
        self.distance_combo.setMaximumWidth(120)
        
        distance_layout.addWidget(distance_label)
        distance_layout.addWidget(self.distance_combo)
        distance_layout.addStretch()
        
        parent_layout.addLayout(distance_layout)
    
    def create_movement_section(self, parent_layout):
        """Create the movement controls section"""
        movement_layout = QHBoxLayout()
        movement_layout.setSpacing(16)
        movement_layout.setContentsMargins(0, 0, 0, 0)
        
        # XY movement grid
        xy_group = self.create_xy_controls()
        movement_layout.addWidget(xy_group)
        
        # Z controls
        z_group = self.create_z_controls()
        movement_layout.addWidget(z_group)
        
        parent_layout.addLayout(movement_layout)
    
    def create_xy_controls(self):
        """Create XY movement controls"""
        xy_frame = QFrame()
        xy_frame.setStyleSheet("""
            QFrame {
                background-color: #232629;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        xy_layout = QVBoxLayout(xy_frame)
        xy_layout.setSpacing(8)
        xy_layout.setContentsMargins(8, 8, 8, 8)
        
        # Label
        xy_label = QLabel("XY Movement")
        xy_label.setAlignment(Qt.AlignCenter)
        xy_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        xy_label.setStyleSheet("color: #f0f0f0; margin-bottom: 4px;")
        xy_layout.addWidget(xy_label)
        
        # Grid layout for buttons
        xy_grid = QGridLayout()
        xy_grid.setSpacing(6)
        
        # Create movement buttons
        self.btn_y_pos = QPushButton("↑")  # Y+
        self.btn_y_neg = QPushButton("↓")  # Y-
        self.btn_x_neg = QPushButton("←")  # X-
        self.btn_x_pos = QPushButton("→")  # X+
        self.btn_xy_home = QPushButton("⌂")  # XY Home
        
        # Set button properties
        xy_buttons = [self.btn_y_pos, self.btn_y_neg, self.btn_x_neg, 
                     self.btn_x_pos, self.btn_xy_home]
        
        for btn in xy_buttons:
            btn.setFixedSize(48, 48)
            btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        
        # Special styling for home button
        self.btn_xy_home.setToolTip("Move XY to home position")
        
        # Arrange buttons in grid
        xy_grid.addWidget(self.btn_y_pos, 0, 1)
        xy_grid.addWidget(self.btn_x_neg, 1, 0)
        xy_grid.addWidget(self.btn_xy_home, 1, 1)
        xy_grid.addWidget(self.btn_x_pos, 1, 2)
        xy_grid.addWidget(self.btn_y_neg, 2, 1)
        
        xy_layout.addLayout(xy_grid)
        return xy_frame
    
    def create_z_controls(self):
        """Create Z movement controls"""
        z_frame = QFrame()
        z_frame.setStyleSheet("""
            QFrame {
                background-color: #232629;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        z_layout = QVBoxLayout(z_frame)
        z_layout.setSpacing(6)
        z_layout.setContentsMargins(8, 8, 8, 8)
        
        # Label
        z_label = QLabel("Z Movement")
        z_label.setAlignment(Qt.AlignCenter)
        z_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        z_label.setStyleSheet("color: #f0f0f0; margin-bottom: 4px;")
        z_layout.addWidget(z_label)
        
        # Z+ button
        self.btn_z_pos = QPushButton("Z+")
        self.btn_z_pos.setFixedSize(64, 52)
        self.btn_z_pos.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_z_pos.setToolTip("Move Z axis up")
        
        # Z home button
        self.btn_z_home = QPushButton("Z⌂")
        self.btn_z_home.setFixedSize(64, 38)
        self.btn_z_home.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_z_home.setToolTip("Move Z to home position")
        
        # Z- button
        self.btn_z_neg = QPushButton("Z-")
        self.btn_z_neg.setFixedSize(64, 52)
        self.btn_z_neg.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_z_neg.setToolTip("Move Z axis down")
        
        z_layout.addWidget(self.btn_z_pos)
        z_layout.addWidget(self.btn_z_home)
        z_layout.addWidget(self.btn_z_neg)
        z_layout.addStretch()
        
        return z_frame
    
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
        self.btn_xy_home.clicked.connect(lambda: self.jog_requested.emit("XY_HOME", 0))
        self.btn_z_home.clicked.connect(lambda: self.jog_requested.emit("Z_HOME", 0))
        
        # Distance selection
        self.distance_combo.currentTextChanged.connect(self.update_jog_distance)
        
        # Emergency stop
        self.btn_emergency.clicked.connect(self.emergency_stop_requested.emit)
    
    def handle_jog(self, direction: JogDirection):
        """Handle jog button clicks"""
        self.jog_requested.emit(direction.value, self.current_jog_distance)
    
    def update_jog_distance(self, text: str):
        """Update the current jog distance"""
        try:
            value = float(text.replace(" mm", ""))
            self.current_jog_distance = value
            # Save to config_manager
            config = self.config_manager.get_jog_config()
            config.step_sizes = self.jog_distances
            self.config_manager.set_jog_config(config)
        except ValueError:
            pass
    
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
        self.distance_combo.setEnabled(enabled)
    
    def get_current_jog_distance(self) -> float:
        """Get the current jog distance"""
        return self.current_jog_distance
    
    def load_jog_config(self):
        config = self.config_manager.get_jog_config()
        if config.step_sizes:
            self.jog_distances = config.step_sizes
            self.distance_combo.clear()
            self.distance_combo.addItems([f"{d} mm" for d in self.jog_distances])
            self.distance_combo.setCurrentText(f"{self.jog_distances[0]} mm")
            self.current_jog_distance = self.jog_distances[0]