# core/config_manager.py

import json
import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import asdict, dataclass
from pathlib import Path
from datetime import datetime
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ActuatorConfig:
    """Actuator configuration dataclass"""
    name: str
    command: str
    enabled: bool = True
    description: str = ""

@dataclass
class AxisConfig:
    """Axis configuration dataclass for type safety"""
    min: float = 0.0
    max: float = 200.0
    acceleration: float = 100.0
    feedrate: float = 1000.0
    jerk: float = 5.0
    homing_speed: float = 500.0
    steps_per_mm: float = 80.0

@dataclass
class ConnectionConfig:
    """Connection configuration dataclass"""
    controller_type: str = "Arduino"
    port: str = ""
    baudrate: int = 115200
    timeout: float = 2.0
    auto_connect: bool = False

@dataclass
class JogConfig:
    """Jog controller configuration"""
    step_sizes: List[float] = None
    park_position: Dict[str, float] = None
    home_position: Dict[str, float] = None
    home_commands: Dict[str, str] = None  # Custom G-code for home commands
    
    def __post_init__(self):
        if self.step_sizes is None:
            self.step_sizes = [0.1, 1.0, 10.0, 100.0]
        if self.park_position is None:
            self.park_position = {"x": 0.0, "y": 0.0, "z": 10.0}
        if self.home_position is None:
            self.home_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        if self.home_commands is None:
            self.home_commands = {
                "all": "G28",
                "x": "G28 X",
                "y": "G28 Y", 
                "z": "G28 Z",
                "xy": "G28 X Y",
                "xz": "G28 X Z",
                "yz": "G28 Y Z"
            }

@dataclass
class UIConfig:
    """UI configuration settings"""
    window_size: Tuple[int, int] = (1200, 800)
    panel_split_ratio: float = 0.7  # Left panel ratio
    theme: str = "light"
    font_size: int = 10
    log_max_lines: int = 1000
    console_max_lines: int = 500

CONFIG_FILE = "data/config.json"
BACKUP_DIR = "data/backups"
MAX_BACKUPS = 5

class ConfigManager:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = Path(config_path)
        self.backup_dir = Path(BACKUP_DIR)
        self.data: Dict[str, Any] = {}
        self._version = "1.0"
        
        self._ensure_directories()
        self._backup_existing_config()
        self.load_config()
        self._migrate_config_if_needed()

    def _ensure_directories(self):
        """Ensure config directory and backup directory exist."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_path.exists():
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration file."""
        default_config = {
            "version": self._version,
            "created": datetime.now().isoformat(),
            "axes": {},
            "actuators": {},
            "connection": {},
            "jog": {},
            "ui": {},
            "macros": {}
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default config at {self.config_path}")

    def _backup_existing_config(self):
        """Create backup of existing config before loading."""
        if self.config_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"config_backup_{timestamp}.json"
            
            try:
                shutil.copy2(self.config_path, backup_path)
                self._cleanup_old_backups()
                logger.info(f"Config backed up to {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to backup config: {e}")

    def _cleanup_old_backups(self):
        """Keep only the latest MAX_BACKUPS backup files."""
        try:
            backup_files = sorted(
                [f for f in self.backup_dir.glob("config_backup_*.json")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backup_files[MAX_BACKUPS:]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    def load_config(self):
        """Load configuration from file with error handling."""
        try:
            with open(self.config_path, 'r') as f:
                self.data = json.load(f)
            logger.info("Configuration loaded successfully")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Failed to load config: {e}")
            self.data = {}
            self._create_default_config()
            self.load_config()

    def save_config(self):
        """Save configuration to file with validation."""
        try:
            # Update timestamp
            self.data["last_modified"] = datetime.now().isoformat()
            
            # Validate JSON before saving
            json_str = json.dumps(self.data, indent=2)
            
            with open(self.config_path, 'w') as f:
                f.write(json_str)
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def _migrate_config_if_needed(self):
        """Handle config version migrations."""
        current_version = self.data.get("version", "0.0")
        if current_version != self._version:
            logger.info(f"Migrating config from {current_version} to {self._version}")
            self.data["version"] = self._version
            self.save_config()

    # -------------------------
    # ✅ Actuator Configuration
    # -------------------------

    def get_actuator_configs(self) -> Dict[str, ActuatorConfig]:
        """Return all actuator configs as ActuatorConfig objects."""
        raw = self.data.get("actuators", {})
        configs = {}
        
        for name, conf in raw.items():
            try:
                configs[name] = ActuatorConfig(**conf)
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid actuator config for {name}: {e}")
                # Create default config for invalid entries
                configs[name] = ActuatorConfig(name=name, command="", enabled=False)
        
        return configs

    def set_actuator_config(self, name: str, config: ActuatorConfig):
        """Set configuration for a single actuator."""
        if "actuators" not in self.data:
            self.data["actuators"] = {}
        
        self.data["actuators"][name] = asdict(config)
        self.save_config()
        logger.info(f"Actuator config updated: {name}")

    def remove_actuator_config(self, name: str) -> bool:
        """Remove an actuator configuration."""
        if "actuators" in self.data and name in self.data["actuators"]:
            del self.data["actuators"][name]
            self.save_config()
            logger.info(f"Actuator config removed: {name}")
            return True
        return False

    def set_actuator_configs(self, configs: Dict[str, ActuatorConfig]):
        """Save all actuator configs."""
        self.data["actuators"] = {
            name: asdict(config) for name, config in configs.items()
        }
        self.save_config()

    # ----------------------
    # ✅ Axis Configuration
    # ----------------------

    def get_axis_config(self, axis: str) -> AxisConfig:
        """Get configuration for a specific axis as AxisConfig object."""
        raw_config = self.data.get("axes", {}).get(axis, {})
        try:
            return AxisConfig(**raw_config)
        except (TypeError, ValueError):
            logger.warning(f"Invalid axis config for {axis}, using defaults")
            return AxisConfig()

    def set_axis_config(self, axis: str, config: AxisConfig):
        """Set configuration for a specific axis."""
        if "axes" not in self.data:
            self.data["axes"] = {}
        
        self.data["axes"][axis] = asdict(config)
        self.save_config()
        logger.info(f"Axis config updated: {axis}")

    def get_all_axis_configs(self) -> Dict[str, AxisConfig]:
        """Get all axes configurations as AxisConfig objects."""
        configs = {}
        for axis in ["x", "y", "z"]:
            configs[axis] = self.get_axis_config(axis)
        return configs

    def set_all_axis_configs(self, configs: Dict[str, AxisConfig]):
        """Set all axes configurations at once."""
        self.data["axes"] = {
            axis: asdict(config) for axis, config in configs.items()
        }
        self.save_config()

    # ----------------------
    # ✅ Connection Configuration
    # ----------------------

    def get_connection_config(self) -> ConnectionConfig:
        """Get connection configuration as ConnectionConfig object."""
        raw_config = self.data.get("connection", {})
        try:
            return ConnectionConfig(**raw_config)
        except (TypeError, ValueError):
            logger.warning("Invalid connection config, using defaults")
            return ConnectionConfig()

    def set_connection_config(self, config: ConnectionConfig):
        """Set connection configuration."""
        self.data["connection"] = asdict(config)
        self.save_config()
        logger.info("Connection config updated")

    # Legacy methods for backward compatibility
    def get_last_port(self) -> str:
        return self.get_connection_config().port

    def set_last_port(self, port: str):
        config = self.get_connection_config()
        config.port = port
        self.set_connection_config(config)

    def get_last_baudrate(self) -> int:
        return self.get_connection_config().baudrate

    def set_last_baudrate(self, baudrate: int):
        config = self.get_connection_config()
        config.baudrate = baudrate
        self.set_connection_config(config)

    def get_last_controller_type(self) -> str:
        return self.get_connection_config().controller_type

    def set_last_controller_type(self, controller_type: str):
        config = self.get_connection_config()
        config.controller_type = controller_type
        self.set_connection_config(config)

    # ----------------------
    # ✅ Jog Configuration
    # ----------------------

    def get_jog_config(self) -> JogConfig:
        """Get jog configuration as JogConfig object."""
        raw_config = self.data.get("jog", {})
        try:
            return JogConfig(**raw_config)
        except (TypeError, ValueError):
            logger.warning("Invalid jog config, using defaults")
            return JogConfig()

    def set_jog_config(self, config: JogConfig):
        """Set jog configuration."""
        self.data["jog"] = asdict(config)
        self.save_config()
        logger.info("Jog config updated")

    # ----------------------
    # ✅ UI Configuration
    # ----------------------

    def get_ui_config(self) -> UIConfig:
        """Get UI configuration as UIConfig object."""
        raw_config = self.data.get("ui", {})
        try:
            return UIConfig(**raw_config)
        except (TypeError, ValueError):
            logger.warning("Invalid UI config, using defaults")
            return UIConfig()

    def set_ui_config(self, config: UIConfig):
        """Set UI configuration."""
        self.data["ui"] = asdict(config)
        self.save_config()
        logger.info("UI config updated")

    # ----------------------
    # ✅ Macro Configuration
    # ----------------------

    def get_macros(self) -> Dict[str, str]:
        """Get all saved macros."""
        return self.data.get("macros", {})

    def set_macro(self, name: str, gcode: str):
        """Set a single macro."""
        if "macros" not in self.data:
            self.data["macros"] = {}
        
        self.data["macros"][name] = gcode
        self.save_config()
        logger.info(f"Macro saved: {name}")

    def remove_macro(self, name: str) -> bool:
        """Remove a macro."""
        if "macros" in self.data and name in self.data["macros"]:
            del self.data["macros"][name]
            self.save_config()
            logger.info(f"Macro removed: {name}")
            return True
        return False

    def set_macros(self, macros: Dict[str, str]):
        """Set all macros at once."""
        self.data["macros"] = macros
        self.save_config()

    # ----------------------
    # ✅ Utility Methods
    # ----------------------

    def reset_to_defaults(self):
        """Reset all configuration to defaults."""
        logger.warning("Resetting configuration to defaults")
        self.data = {}
        self._create_default_config()
        self.load_config()

    def export_config(self, export_path: str) -> bool:
        """Export configuration to a file."""
        try:
            with open(export_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Config exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False

    def import_config(self, import_path: str) -> bool:
        """Import configuration from a file."""
        try:
            with open(import_path, 'r') as f:
                imported_data = json.load(f)
            
            # Backup current config before importing
            self._backup_existing_config()
            
            self.data = imported_data
            self.save_config()
            logger.info(f"Config imported from {import_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False

    def get_config_info(self) -> Dict[str, Any]:
        """Get information about the current configuration."""
        return {
            "version": self.data.get("version", "unknown"),
            "created": self.data.get("created", "unknown"),
            "last_modified": self.data.get("last_modified", "unknown"),
            "config_file": str(self.config_path),
            "file_size": self.config_path.stat().st_size if self.config_path.exists() else 0,
            "actuators_count": len(self.data.get("actuators", {})),
            "macros_count": len(self.data.get("macros", {}))
        }