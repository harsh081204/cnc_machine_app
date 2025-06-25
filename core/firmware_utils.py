# core/firmware_utils.py

import re
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import time

# Setup logging
logger = logging.getLogger(__name__)

class FirmwareType(Enum):
    """Enumeration of supported firmware types"""
    GRBL = "GRBL"
    MARLIN = "Marlin"
    SMOOTHIEWARE = "Smoothieware"
    REPETIER = "Repetier"
    INVARIANCE = "Invariance"
    UNKNOWN = "Unknown"

@dataclass
class FirmwareInfo:
    """Complete firmware information"""
    name: str
    version: str = "Unknown"
    build_date: Optional[str] = None
    protocol_version: Optional[str] = None
    machine_type: Optional[str] = None
    capabilities: List[str] = None
    buffer_size: Optional[int] = None
    max_feed_rate: Optional[int] = None
    build_info: Optional[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

@dataclass
class FirmwareCommand:
    """Firmware-specific command configuration"""
    initialization: List[str]
    status_query: str
    home_command: str
    reset_command: str
    unlock_command: Optional[str] = None
    position_query: str = "?"
    version_query: str = "$I"

class FirmwareUtils:
    """
    Enhanced utilities for detecting and managing firmware types and capabilities.
    """
    
    # Enhanced firmware detection patterns
    FIRMWARE_PATTERNS = {
        FirmwareType.GRBL: {
            "version": re.compile(r"Grbl\s+([\d.]+[a-z]*)", re.IGNORECASE),
            "welcome": re.compile(r"Grbl\s+([\d.]+[a-z]*)\s*\[(.+?)\]", re.IGNORECASE),
            "build_info": re.compile(r"\[VER:([\d.]+[a-z]*):(.+?)\]", re.IGNORECASE),
            "capabilities": re.compile(r"\[OPT:([MVHNPL,]+)\]", re.IGNORECASE)
        },
        FirmwareType.MARLIN: {
            "version": re.compile(r"FIRMWARE_NAME:Marlin\s+([\w.\-]+)", re.IGNORECASE),
            "build_date": re.compile(r"MACHINE_TYPE:(.+?)\s+EXTRUDER_COUNT", re.IGNORECASE),
            "protocol": re.compile(r"PROTOCOL_VERSION:([\d.]+)", re.IGNORECASE),
            "capabilities": re.compile(r"MACHINE_TYPE:(.+?)\s", re.IGNORECASE)
        },
        FirmwareType.SMOOTHIEWARE: {
            "version": re.compile(r"Smoothie\s+version\s+([\w.\-]+)", re.IGNORECASE),
            "build_date": re.compile(r"Build\s+date:\s*(.+)", re.IGNORECASE),
            "capabilities": re.compile(r"Build\s+on:\s*(.+)", re.IGNORECASE)
        },
        FirmwareType.REPETIER: {
            "version": re.compile(r"FIRMWARE_NAME:Repetier\s+([\w.\-]+)", re.IGNORECASE),
            "protocol": re.compile(r"PROTOCOL_VERSION:([\d.]+)", re.IGNORECASE),
            "capabilities": re.compile(r"MACHINE_TYPE:(.+)", re.IGNORECASE)
        },
        FirmwareType.INVARIANCE: {
            "version": re.compile(r"INVARIANCE[_\s]*CNC\s+([\d.\-]+)", re.IGNORECASE),
            "build_info": re.compile(r"INVARIANCE_BUILD:(.+)", re.IGNORECASE),
            "capabilities": re.compile(r"INVARIANCE_CAP:(.+)", re.IGNORECASE),
            "buffer": re.compile(r"INVARIANCE_BUF:(\d+)", re.IGNORECASE)
        }
    }
    
    # Firmware-specific commands
    FIRMWARE_COMMANDS = {
        FirmwareType.GRBL: FirmwareCommand(
            initialization=["$X", "G21", "G90", "G94"],  # Unlock, metric, absolute, feed rate mode
            status_query="?",
            home_command="$H",
            reset_command="\x18",  # Ctrl+X
            unlock_command="$X",
            position_query="?",
            version_query="$I"
        ),
        FirmwareType.MARLIN: FirmwareCommand(
            initialization=["M115", "G21", "G90", "M82"],  # Get firmware info, metric, absolute, absolute extruder
            status_query="M114",
            home_command="G28",
            reset_command="M999",
            position_query="M114",
            version_query="M115"
        ),
        FirmwareType.SMOOTHIEWARE: FirmwareCommand(
            initialization=["version", "G21", "G90"],
            status_query="M114",
            home_command="G28",
            reset_command="reset",
            position_query="M114",
            version_query="version"
        ),
        FirmwareType.REPETIER: FirmwareCommand(
            initialization=["M115", "G21", "G90"],
            status_query="M114",
            home_command="G28",
            reset_command="M999",
            position_query="M114",
            version_query="M115"
        ),
        FirmwareType.INVARIANCE: FirmwareCommand(
            initialization=["INVARIANCE_INIT", "G21", "G90"],
            status_query="INVARIANCE_STATUS",
            home_command="INVARIANCE_HOME",
            reset_command="INVARIANCE_RESET",
            unlock_command="INVARIANCE_UNLOCK",
            position_query="INVARIANCE_POS",
            version_query="INVARIANCE_VER"
        )
    }
    
    # Known capability codes for different firmware
    CAPABILITY_CODES = {
        FirmwareType.GRBL: {
            'V': 'Variable spindle enabled',
            'N': 'Line numbers enabled',
            'M': 'Mist coolant enabled',
            'C': 'CoreXY enabled',
            'P': 'Parking motion enabled',
            'Z': 'Homing force origin enabled',
            'H': 'Homing single axis enabled',
            'T': 'Two limit switches on axis enabled',
            'A': 'Allow feed rate overrides in probe cycles',
            'D': 'Use spindle direction as enable pin',
            'L': 'Homing locate cycle',
            'S': 'Spindle enable pin as spindle direction pin'
        }
    }
    
    def __init__(self):
        self.detection_history: List[Tuple[str, str, float]] = []  # (response, detected_firmware, timestamp)
        self.current_firmware: Optional[FirmwareInfo] = None
        
    @staticmethod
    def detect_firmware_type(response: str) -> FirmwareType:
        """
        Detect firmware type from serial response.
        
        Args:
            response (str): Raw text output from firmware
            
        Returns:
            FirmwareType: Detected firmware type or UNKNOWN
        """
        response_clean = response.strip()
        
        for firmware_type, patterns in FirmwareUtils.FIRMWARE_PATTERNS.items():
            for pattern_name, pattern in patterns.items():
                if pattern.search(response_clean):
                    logger.info(f"Detected {firmware_type.value} firmware via {pattern_name} pattern")
                    return firmware_type
                    
        logger.warning(f"Unknown firmware response: {response_clean[:100]}...")
        return FirmwareType.UNKNOWN
    
    def extract_firmware_info(self, response: str) -> FirmwareInfo:
        """
        Extract comprehensive firmware information from response.
        
        Args:
            response (str): Serial response string
            
        Returns:
            FirmwareInfo: Complete firmware information
        """
        firmware_type = self.detect_firmware_type(response)
        
        if firmware_type == FirmwareType.UNKNOWN:
            return FirmwareInfo(name="Unknown", version="Unknown")
            
        patterns = self.FIRMWARE_PATTERNS[firmware_type]
        info = FirmwareInfo(name=firmware_type.value)
        
        # Extract version
        if "version" in patterns:
            match = patterns["version"].search(response)
            if match:
                info.version = match.group(1)
                
        # Extract build date
        if "build_date" in patterns:
            match = patterns["build_date"].search(response)
            if match:
                info.build_date = match.group(1).strip()
                
        # Extract protocol version
        if "protocol" in patterns:
            match = patterns["protocol"].search(response)
            if match:
                info.protocol_version = match.group(1)
                
        # Extract build info
        if "build_info" in patterns:
            match = patterns["build_info"].search(response)
            if match:
                info.build_info = match.group(1).strip()
                
        # Extract capabilities
        if "capabilities" in patterns:
            match = patterns["capabilities"].search(response)
            if match:
                capabilities_str = match.group(1)
                info.capabilities = self._parse_capabilities(firmware_type, capabilities_str)
                
        # Extract buffer size for supported firmware
        if firmware_type == FirmwareType.INVARIANCE and "buffer" in patterns:
            match = patterns["buffer"].search(response)
            if match:
                info.buffer_size = int(match.group(1))
                
        # Record detection
        self.detection_history.append((response[:200], firmware_type.value, time.time()))
        self.current_firmware = info
        
        logger.info(f"Extracted firmware info: {info.name} v{info.version}")
        return info
    
    def _parse_capabilities(self, firmware_type: FirmwareType, capabilities_str: str) -> List[str]:
        """Parse capability codes into human-readable descriptions."""
        capabilities = []
        
        if firmware_type == FirmwareType.GRBL:
            # GRBL uses single-letter codes
            for code in capabilities_str:
                if code in self.CAPABILITY_CODES[FirmwareType.GRBL]:
                    capabilities.append(self.CAPABILITY_CODES[FirmwareType.GRBL][code])
                else:
                    capabilities.append(f"Unknown capability: {code}")
        else:
            # Other firmware may use different formats
            capabilities.append(capabilities_str.strip())
            
        return capabilities
    
    def get_commands_for_firmware(self, firmware_type: FirmwareType) -> Optional[FirmwareCommand]:
        """
        Get command set for specific firmware type.
        
        Args:
            firmware_type (FirmwareType): Firmware type
            
        Returns:
            Optional[FirmwareCommand]: Command configuration or None
        """
        return self.FIRMWARE_COMMANDS.get(firmware_type)
    
    def is_supported_firmware(self, response: str) -> bool:
        """
        Check if firmware is supported by the system.
        
        Args:
            response (str): Firmware response
            
        Returns:
            bool: True if supported
        """
        detected_type = self.detect_firmware_type(response)
        return detected_type != FirmwareType.UNKNOWN
    
    def get_initialization_sequence(self, firmware_type: FirmwareType) -> List[str]:
        """
        Get initialization command sequence for firmware.
        
        Args:
            firmware_type (FirmwareType): Firmware type
            
        Returns:
            List[str]: List of initialization commands
        """
        commands = self.get_commands_for_firmware(firmware_type)
        return commands.initialization if commands else []
    
    def suggest_connection_settings(self, firmware_type: FirmwareType) -> Dict[str, Any]:
        """
        Suggest optimal connection settings for firmware type.
        
        Args:
            firmware_type (FirmwareType): Firmware type
            
        Returns:
            Dict[str, Any]: Suggested settings
        """
        settings = {
            FirmwareType.GRBL: {
                "baudrate": 115200,
                "timeout": 10,
                "line_ending": "\n",
                "echo": False,
                "flow_control": False
            },
            FirmwareType.MARLIN: {
                "baudrate": 250000,
                "timeout": 10,
                "line_ending": "\n",
                "echo": True,
                "flow_control": False
            },
            FirmwareType.SMOOTHIEWARE: {
                "baudrate": 115200,
                "timeout": 10,
                "line_ending": "\n",
                "echo": False,
                "flow_control": False
            },
            FirmwareType.REPETIER: {
                "baudrate": 250000,
                "timeout": 10,
                "line_ending": "\n",
                "echo": True,
                "flow_control": False
            },
            FirmwareType.INVARIANCE: {
                "baudrate": 115200,
                "timeout": 5,
                "line_ending": "\n",
                "echo": False,
                "flow_control": True
            }
        }
        
        return settings.get(firmware_type, {
            "baudrate": 115200,
            "timeout": 10,
            "line_ending": "\n",
            "echo": False,
            "flow_control": False
        })
    
    def validate_firmware_response(self, response: str, expected_firmware: FirmwareType) -> bool:
        """
        Validate if response matches expected firmware type.
        
        Args:
            response (str): Firmware response
            expected_firmware (FirmwareType): Expected firmware type
            
        Returns:
            bool: True if response matches expected firmware
        """
        detected = self.detect_firmware_type(response)
        return detected == expected_firmware
    
    def get_detection_confidence(self, response: str) -> float:
        """
        Calculate confidence level of firmware detection.
        
        Args:
            response (str): Firmware response
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        firmware_type = self.detect_firmware_type(response)
        
        if firmware_type == FirmwareType.UNKNOWN:
            return 0.0
            
        patterns = self.FIRMWARE_PATTERNS[firmware_type]
        matches = 0
        total_patterns = len(patterns)
        
        for pattern in patterns.values():
            if pattern.search(response):
                matches += 1
                
        return matches / total_patterns if total_patterns > 0 else 0.0
    
    def get_detection_history(self) -> List[Dict[str, Any]]:
        """
        Get firmware detection history.
        
        Returns:
            List[Dict]: Detection history with timestamps
        """
        return [
            {
                "response": response,
                "firmware": firmware,
                "timestamp": timestamp,
                "time_ago": time.time() - timestamp
            }
            for response, firmware, timestamp in self.detection_history
        ]
    
    def clear_detection_history(self):
        """Clear the detection history."""
        self.detection_history.clear()
        logger.info("Firmware detection history cleared")
    
    def export_firmware_info(self) -> Dict[str, Any]:
        """
        Export current firmware information as dictionary.
        
        Returns:
            Dict[str, Any]: Firmware information
        """
        if not self.current_firmware:
            return {"error": "No firmware detected"}
            
        return {
            "name": self.current_firmware.name,
            "version": self.current_firmware.version,
            "build_date": self.current_firmware.build_date,
            "protocol_version": self.current_firmware.protocol_version,
            "machine_type": self.current_firmware.machine_type,
            "capabilities": self.current_firmware.capabilities,
            "buffer_size": self.current_firmware.buffer_size,
            "max_feed_rate": self.current_firmware.max_feed_rate,
            "build_info": self.current_firmware.build_info,
            "detection_confidence": self.get_detection_confidence("") if self.detection_history else 0.0,
            "last_detection": self.detection_history[-1][2] if self.detection_history else None
        }
    
    @staticmethod
    def get_firmware_documentation_url(firmware_type: FirmwareType) -> Optional[str]:
        """
        Get documentation URL for firmware type.
        
        Args:
            firmware_type (FirmwareType): Firmware type
            
        Returns:
            Optional[str]: Documentation URL or None
        """
        urls = {
            FirmwareType.GRBL: "https://github.com/gnea/grbl/wiki",
            FirmwareType.MARLIN: "https://marlinfw.org/docs/",
            FirmwareType.SMOOTHIEWARE: "https://smoothieware.org/",
            FirmwareType.REPETIER: "https://www.repetier.com/documentation/",
            FirmwareType.INVARIANCE: "https://invariance-automation.com/docs/"
        }
        return urls.get(firmware_type)
    
    @staticmethod
    def format_firmware_info(info: FirmwareInfo) -> str:
        """
        Format firmware information for display.
        
        Args:
            info (FirmwareInfo): Firmware information
            
        Returns:
            str: Formatted string
        """
        lines = [f"Firmware: {info.name} v{info.version}"]
        
        if info.build_date:
            lines.append(f"Build Date: {info.build_date}")
        if info.protocol_version:
            lines.append(f"Protocol: {info.protocol_version}")
        if info.machine_type:
            lines.append(f"Machine: {info.machine_type}")
        if info.buffer_size:
            lines.append(f"Buffer Size: {info.buffer_size} bytes")
        if info.capabilities:
            lines.append(f"Capabilities: {', '.join(info.capabilities)}")
        if info.build_info:
            lines.append(f"Build Info: {info.build_info}")
            
        return "\n".join(lines)