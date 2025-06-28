# core/gcode_parser.py
import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

class MovementType(Enum):
    """Types of G-code movement commands"""
    RAPID = "G0"
    LINEAR = "G1"
    ARC_CW = "G2"
    ARC_CCW = "G3"
    DWELL = "G4"
    HOME = "G28"
    ABSOLUTE = "G90"
    RELATIVE = "G91"

@dataclass
class MovementCommand:
    """Parsed movement command data"""
    command_type: MovementType
    coordinates: Dict[str, float]
    feedrate: Optional[float] = None
    is_relative: bool = False
    is_homing: bool = False

class GCodeParser:
    """G-code parser for extracting movement commands and coordinates"""
    
    def __init__(self):
        # Regex patterns for parsing G-code
        self.movement_pattern = re.compile(r'G([0-3])\s*([XYZIJKRF][-+]?\d*\.?\d*\s*)*', re.IGNORECASE)
        self.coordinate_pattern = re.compile(r'([XYZIJKRF])([-+]?\d*\.?\d*)', re.IGNORECASE)
        self.feedrate_pattern = re.compile(r'F(\d*\.?\d*)', re.IGNORECASE)
        self.home_pattern = re.compile(r'G28\s*([XYZ]*)', re.IGNORECASE)
        self.mode_pattern = re.compile(r'G(90|91)', re.IGNORECASE)
        
    def parse_command(self, gcode: str) -> Optional[MovementCommand]:
        """Parse a G-code command and extract movement information"""
        gcode = gcode.strip().upper()
        
        # Check if it's a movement command
        if not self.is_movement_command(gcode):
            return None
            
        # Parse coordinates
        coordinates = self.extract_coordinates(gcode)
        
        # Parse feedrate
        feedrate = self.extract_feedrate(gcode)
        
        # Determine command type
        command_type = self.get_command_type(gcode)
        
        # Check if it's relative positioning
        is_relative = self.is_relative_positioning(gcode)
        
        # Check if it's a homing command
        is_homing = self.is_homing_command(gcode)
        
        return MovementCommand(
            command_type=command_type,
            coordinates=coordinates,
            feedrate=feedrate,
            is_relative=is_relative,
            is_homing=is_homing
        )
    
    def is_movement_command(self, gcode: str) -> bool:
        """Check if the G-code command is a movement command"""
        return bool(self.movement_pattern.match(gcode) or 
                   self.home_pattern.match(gcode) or
                   self.mode_pattern.match(gcode))
    
    def extract_coordinates(self, gcode: str) -> Dict[str, float]:
        """Extract coordinate values from G-code"""
        coordinates = {}
        matches = self.coordinate_pattern.findall(gcode)
        
        for axis, value in matches:
            axis = axis.upper()
            if value:  # Only add if there's a value
                try:
                    coordinates[axis] = float(value)
                except ValueError:
                    continue
        
        return coordinates
    
    def extract_feedrate(self, gcode: str) -> Optional[float]:
        """Extract feedrate value from G-code"""
        match = self.feedrate_pattern.search(gcode)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def get_command_type(self, gcode: str) -> MovementType:
        """Determine the type of movement command"""
        if gcode.startswith('G0'):
            return MovementType.RAPID
        elif gcode.startswith('G1'):
            return MovementType.LINEAR
        elif gcode.startswith('G2'):
            return MovementType.ARC_CW
        elif gcode.startswith('G3'):
            return MovementType.ARC_CCW
        elif gcode.startswith('G4'):
            return MovementType.DWELL
        elif gcode.startswith('G28'):
            return MovementType.HOME
        elif gcode.startswith('G90'):
            return MovementType.ABSOLUTE
        elif gcode.startswith('G91'):
            return MovementType.RELATIVE
        else:
            return MovementType.LINEAR  # Default
    
    def is_relative_positioning(self, gcode: str) -> bool:
        """Check if the command uses relative positioning"""
        return gcode.startswith('G91')
    
    def is_homing_command(self, gcode: str) -> bool:
        """Check if the command is a homing command"""
        return gcode.startswith('G28')
    
    def parse_multiple_commands(self, gcode_block: str) -> List[MovementCommand]:
        """Parse multiple G-code commands in a block"""
        commands = []
        lines = gcode_block.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(';'):  # Skip empty lines and comments
                command = self.parse_command(line)
                if command:
                    commands.append(command)
        
        return commands 