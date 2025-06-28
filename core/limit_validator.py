# core/limit_validator.py
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from core.gcode_parser import MovementCommand, GCodeParser
from core.config_manager import ConfigManager

@dataclass
class ValidationResult:
    """Result of limit validation"""
    is_valid: bool
    error_message: Optional[str] = None
    axis: Optional[str] = None
    requested_position: Optional[float] = None
    limit_value: Optional[float] = None

class LimitValidator:
    """Validator for checking G-code commands against configured limits"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.gcode_parser = GCodeParser()
        self.current_position = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}  # Track current position
        self.is_relative_mode = False  # Track positioning mode
        
    def validate_command(self, gcode: str) -> ValidationResult:
        """Validate a G-code command against configured limits"""
        # Parse the command
        movement_cmd = self.gcode_parser.parse_command(gcode)
        
        if not movement_cmd:
            # Not a movement command, allow it
            return ValidationResult(is_valid=True)
        
        # Handle positioning mode changes
        if movement_cmd.command_type.value in ['G90', 'G91']:
            self.is_relative_mode = (movement_cmd.command_type.value == 'G91')
            return ValidationResult(is_valid=True)
        
        # Handle homing commands (always allow)
        if movement_cmd.is_homing:
            return ValidationResult(is_valid=True)
        
        # Get axis limits from config
        axis_configs = self.config_manager.get_all_axis_configs()
        
        # Validate each axis in the command
        for axis, value in movement_cmd.coordinates.items():
            if axis in ['X', 'Y', 'Z']:
                result = self._validate_axis_position(axis, value, axis_configs.get(axis.lower(), {}))
                if not result.is_valid:
                    return result
        
        # Update current position if command is valid
        self._update_position(movement_cmd)
        
        return ValidationResult(is_valid=True)
    
    def _validate_axis_position(self, axis: str, value: float, axis_config: Dict) -> ValidationResult:
        """Validate a single axis position against its limits"""
        # Get limits from config - handle both dict and dataclass
        if hasattr(axis_config, 'min') and hasattr(axis_config, 'max'):
            # It's an AxisConfig dataclass
            min_limit = axis_config.min
            max_limit = axis_config.max
        else:
            # It's a dictionary
            min_limit = axis_config.get('min', 0.0)
            max_limit = axis_config.get('max', 200.0)
        
        # Calculate target position
        if self.is_relative_mode:
            target_position = self.current_position[axis] + value
        else:
            target_position = value
        
        # Check against limits
        if target_position < min_limit:
            return ValidationResult(
                is_valid=False,
                error_message=f"{axis}-axis position {target_position:.3f}mm is below minimum limit of {min_limit:.3f}mm",
                axis=axis,
                requested_position=target_position,
                limit_value=min_limit
            )
        
        if target_position > max_limit:
            return ValidationResult(
                is_valid=False,
                error_message=f"{axis}-axis position {target_position:.3f}mm is above maximum limit of {max_limit:.3f}mm",
                axis=axis,
                requested_position=target_position,
                limit_value=max_limit
            )
        
        return ValidationResult(is_valid=True)
    
    def _update_position(self, movement_cmd: MovementCommand):
        """Update current position based on the movement command"""
        for axis, value in movement_cmd.coordinates.items():
            if axis in ['X', 'Y', 'Z']:
                if self.is_relative_mode:
                    self.current_position[axis] += value
                else:
                    self.current_position[axis] = value
    
    def set_current_position(self, position: Dict[str, float]):
        """Set the current machine position (e.g., from status updates)"""
        for axis in ['X', 'Y', 'Z']:
            if axis in position:
                self.current_position[axis] = position[axis]
    
    def get_current_position(self) -> Dict[str, float]:
        """Get the current tracked position"""
        return self.current_position.copy()
    
    def validate_multiple_commands(self, gcode_block: str) -> List[ValidationResult]:
        """Validate multiple G-code commands in a block"""
        results = []
        commands = self.gcode_parser.parse_multiple_commands(gcode_block)
        
        for command in commands:
            # Convert command back to string for validation
            gcode_str = self._command_to_string(command)
            result = self.validate_command(gcode_str)
            results.append(result)
            
            # Stop on first error
            if not result.is_valid:
                break
        
        return results
    
    def _command_to_string(self, command: MovementCommand) -> str:
        """Convert a MovementCommand back to G-code string"""
        parts = [command.command_type.value]
        
        for axis, value in command.coordinates.items():
            parts.append(f"{axis}{value}")
        
        if command.feedrate:
            parts.append(f"F{command.feedrate}")
        
        return " ".join(parts)
    
    def reset_position(self):
        """Reset current position to origin"""
        self.current_position = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}
        self.is_relative_mode = False 