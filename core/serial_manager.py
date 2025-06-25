import serial
import serial.tools.list_ports
import threading
import time
import queue
import re
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, QTimer


class FirmwareType(Enum):
    """Supported firmware types"""
    UNKNOWN = "Unknown"
    GRBL = "GRBL"
    MARLIN = "Marlin"
    REPETIER = "Repetier"
    SMOOTHIEWARE = "Smoothieware"
    KLIPPER = "Klipper"
    CUSTOM = "Custom"


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    ERROR = "Error"


@dataclass
class SerialResponse:
    """Structured response from serial communication"""
    raw_data: str
    timestamp: float
    response_type: str  # 'ok', 'error', 'status', 'data', 'firmware'
    parsed_data: Optional[Dict[str, Any]] = None


@dataclass
class ConnectionInfo:
    """Information about current connection"""
    port: str
    baudrate: int
    firmware: FirmwareType
    state: ConnectionState
    connected_at: Optional[float] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    commands_sent: int = 0
    responses_received: int = 0


class SerialManager(QObject):
    """
    Enhanced serial communication manager for CNC controllers.
    Provides robust connection handling, firmware detection, and command queuing.
    """
    
    # Signals
    data_received = Signal(SerialResponse)          # Structured response data
    raw_data_received = Signal(str)                 # Raw string data for logging
    connection_status_changed = Signal(ConnectionState)  # Connection state changes
    connection_info_updated = Signal(ConnectionInfo)     # Connection statistics
    error_occurred = Signal(str)                    # Error messages
    firmware_detected = Signal(FirmwareType, dict) # Firmware type and info
    command_queued = Signal(str)                   # Command added to queue
    command_sent = Signal(str)                     # Command actually sent
    response_timeout = Signal(str)                 # Command timed out
    coordinates_updated = Signal(dict)             # Emitted when new coordinates are parsed from a line
    
    def __init__(self, auto_reconnect: bool = True, command_timeout: float = 5.0):
        super().__init__()
        
        # Connection management
        self.serial_port: Optional[serial.Serial] = None
        self.connection_info = ConnectionInfo("", 0, FirmwareType.UNKNOWN, ConnectionState.DISCONNECTED)
        
        # Threading
        self.read_thread: Optional[threading.Thread] = None
        self.write_thread: Optional[threading.Thread] = None
        self.keep_running = False
        
        # Command queue and response handling
        self.command_queue = queue.Queue()
        self.pending_commands = {}  # command_id -> (command, timestamp, callback)
        self.command_counter = 0
        self.command_timeout = command_timeout
        
        # Auto-reconnect functionality
        self.auto_reconnect = auto_reconnect
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0  # seconds
        
        # Firmware detection
        self.firmware_info = {}
        self.firmware_detection_commands = {
            FirmwareType.GRBL: ["$I", "$$"],
            FirmwareType.MARLIN: ["M115", "M503"],
            FirmwareType.REPETIER: ["M115", "M205"],
            FirmwareType.SMOOTHIEWARE: ["version", "config"],
            FirmwareType.KLIPPER: ["STATUS", "HELP"]
        }
        
        # Response parsers
        self.response_parsers = {
            'grbl_status': re.compile(r'<([^>]+)>'),
            'grbl_setting': re.compile(r'\$(\d+)=([^\r\n]+)'),
            'marlin_temp': re.compile(r'T:(\d+\.?\d*)\s*/(\d+\.?\d*)'),
            'marlin_pos': re.compile(r'X:([+-]?\d+\.?\d*)\s*Y:([+-]?\d+\.?\d*)\s*Z:([+-]?\d+\.?\d*)'),
            'error': re.compile(r'(error|Error|ERROR|ALARM)[:|\s]*(.*)'),
        }
        
        # Statistics and monitoring
        self.last_activity = time.time()
        self.heartbeat_interval = 30.0  # seconds
        self.setup_monitoring()
    
    def setup_monitoring(self):
        """Setup periodic monitoring and maintenance tasks"""
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._periodic_maintenance)
        self.monitor_timer.start(1000)  # Run every second
    
    def get_available_ports(self) -> List[tuple]:
        """Get list of available serial ports"""
        try:
            ports = serial.tools.list_ports.comports()
            return [(port.device, port.description, port.hwid) for port in ports]
        except Exception as e:
            self.error_occurred.emit(f"Failed to enumerate ports: {e}")
            return []
    
    def connect(self, port_name: str, baudrate: int, timeout: float = 1.0, 
                write_timeout: float = 1.0, **kwargs):
        """
        Establish connection with enhanced parameters and error handling
        """
        if self.is_connected():
            self.disconnect()
        
        self._update_connection_state(ConnectionState.CONNECTING)
        
        try:
            # Configure serial port with advanced settings
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=write_timeout,
                bytesize=kwargs.get('bytesize', serial.EIGHTBITS),
                parity=kwargs.get('parity', serial.PARITY_NONE),
                stopbits=kwargs.get('stopbits', serial.STOPBITS_ONE),
                xonxoff=kwargs.get('xonxoff', False),
                rtscts=kwargs.get('rtscts', False),
                dsrdtr=kwargs.get('dsrdtr', False)
            )
            
            # Update connection info
            self.connection_info.port = port_name
            self.connection_info.baudrate = baudrate
            self.connection_info.connected_at = time.time()
            self.connection_info.bytes_sent = 0
            self.connection_info.bytes_received = 0
            self.connection_info.commands_sent = 0
            self.connection_info.responses_received = 0
            
            # Start communication threads
            self.keep_running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True, name="SerialReader")
            self.write_thread = threading.Thread(target=self._write_loop, daemon=True, name="SerialWriter")
            
            self.read_thread.start()
            self.write_thread.start()
            
            # Reset reconnect attempts on successful connection
            self.reconnect_attempts = 0
            
            self._update_connection_state(ConnectionState.CONNECTED)
            
            # Start firmware detection
            self._detect_firmware()
            
            return True
            
        except serial.SerialException as e:
            self.serial_port = None
            self._update_connection_state(ConnectionState.ERROR)
            self.error_occurred.emit(f"Serial connection failed: {e}")
            
            # Attempt auto-reconnect if enabled
            if self.auto_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
                self._schedule_reconnect()
            
            return False
        except Exception as e:
            self.serial_port = None
            self._update_connection_state(ConnectionState.ERROR)
            self.error_occurred.emit(f"Unexpected connection error: {e}")
            return False
    
    def disconnect(self):
        """Safely disconnect from serial port"""
        self.keep_running = False
        
        # Clear command queue
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except queue.Empty:
                break
        
        # Close serial port
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as e:
                self.error_occurred.emit(f"Error closing serial port: {e}")
        
        self.serial_port = None
        
        # Wait for threads to finish
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        if self.write_thread and self.write_thread.is_alive():
            self.write_thread.join(timeout=2.0)
        
        self._update_connection_state(ConnectionState.DISCONNECTED)
    
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return (self.serial_port is not None and 
                self.serial_port.is_open and 
                self.connection_info.state == ConnectionState.CONNECTED)
    
    def send_command(self, command: str, priority: int = 5, 
                    callback: Optional[Callable] = None, 
                    expect_response: bool = True) -> Optional[int]:
        """
        Send command with priority queue and response tracking
        
        Args:
            command: G-code or other command to send
            priority: Priority level (1=highest, 10=lowest)
            callback: Optional callback for response
            expect_response: Whether to wait for and track response
        
        Returns:
            Command ID for tracking, or None if failed
        """
        if not self.is_connected():
            self.error_occurred.emit("Cannot send command: Not connected")
            return None
        
        # Generate command ID
        self.command_counter += 1
        command_id = self.command_counter
        
        # Clean and validate command
        clean_command = command.strip()
        if not clean_command:
            self.error_occurred.emit("Cannot send empty command")
            return None
        
        # Add to queue with metadata
        command_data = {
            'id': command_id,
            'command': clean_command,
            'priority': priority,
            'callback': callback,
            'expect_response': expect_response,
            'timestamp': time.time(),
            'retries': 0
        }
        
        try:
            self.command_queue.put((priority, command_data))
            self.command_queued.emit(clean_command)
            
            if expect_response:
                self.pending_commands[command_id] = command_data
            
            return command_id
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to queue command: {e}")
            return None
    
    def send_immediate(self, command: str) -> bool:
        """Send command immediately, bypassing queue (use sparingly)"""
        if not self.is_connected():
            return False
        
        try:
            full_command = (command.strip() + "\n").encode('utf-8')
            self.serial_port.write(full_command)
            self.serial_port.flush()
            
            # Update statistics
            self.connection_info.bytes_sent += len(full_command)
            self.connection_info.commands_sent += 1
            self.last_activity = time.time()
            
            self.command_sent.emit(command.strip())
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to send immediate command: {e}")
            return False
    
    def get_connection_info(self) -> ConnectionInfo:
        """Get current connection information and statistics"""
        return self.connection_info
    
    def get_firmware_info(self) -> Dict[str, Any]:
        """Get detected firmware information"""
        return self.firmware_info.copy()
    
    def clear_buffers(self):
        """Clear input/output buffers"""
        if self.is_connected():
            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
            except Exception as e:
                self.error_occurred.emit(f"Failed to clear buffers: {e}")
    
    def _update_connection_state(self, new_state: ConnectionState):
        """Update connection state and emit signal"""
        if self.connection_info.state != new_state:
            self.connection_info.state = new_state
            self.connection_status_changed.emit(new_state)
            self.connection_info_updated.emit(self.connection_info)
    
    def _read_loop(self):
        """Main reading loop running in separate thread"""
        buffer = ""
        coord_regex = re.compile(r'X:([+-]?\d+\.?\d*)\s*Y:([+-]?\d+\.?\d*)\s*Z:([+-]?\d+\.?\d*)')
        while self.keep_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    self.connection_info.bytes_received += len(data.encode('utf-8'))
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            self.last_activity = time.time()
                            self.connection_info.responses_received += 1
                            
                            # Emit raw data
                            self.raw_data_received.emit(line)
                            
                            # Coordinate extraction (Marlin/GRBL style)
                            match = coord_regex.search(line)
                            if match:
                                coords = {
                                    'X': float(match.group(1)),
                                    'Y': float(match.group(2)),
                                    'Z': float(match.group(3)),
                                }
                                self.coordinates_updated.emit(coords)
                            
                            # Parse and emit structured response
                            response = self._parse_response(line)
                            self.data_received.emit(response)
                            
                            # Handle response for pending commands
                            self._handle_response(response)
                
                else:
                    time.sleep(0.01)  # Small delay when no data available
                
            except serial.SerialException as e:
                self.error_occurred.emit(f"Serial read error: {e}")
                if self.auto_reconnect:
                    self._schedule_reconnect()
                break
            except Exception as e:
                self.error_occurred.emit(f"Unexpected read error: {e}")
                break
    
    def _write_loop(self):
        """Command writing loop with priority queue"""
        while self.keep_running and self.serial_port and self.serial_port.is_open:
            try:
                # Get command from priority queue (blocks with timeout)
                try:
                    priority, command_data = self.command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                command = command_data['command']
                command_id = command_data['id']
                
                # Send command
                full_command = (command + "\n").encode('utf-8')
                self.serial_port.write(full_command)
                self.serial_port.flush()
                
                # Update statistics
                self.connection_info.bytes_sent += len(full_command)
                self.connection_info.commands_sent += 1
                self.last_activity = time.time()
                
                # Emit signal
                self.command_sent.emit(command)
                
                # Mark task as done
                self.command_queue.task_done()
                
            except serial.SerialException as e:
                self.error_occurred.emit(f"Serial write error: {e}")
                if self.auto_reconnect:
                    self._schedule_reconnect()
                break
            except Exception as e:
                self.error_occurred.emit(f"Unexpected write error: {e}")
                break
    
    def _parse_response(self, raw_data: str) -> SerialResponse:
        """Parse raw response into structured format"""
        response = SerialResponse(
            raw_data=raw_data,
            timestamp=time.time(),
            response_type='data'
        )
        
        # Determine response type and parse accordingly
        raw_lower = raw_data.lower()
        
        if any(keyword in raw_lower for keyword in ['ok', 'done', 'wait']):
            response.response_type = 'ok'
        elif any(keyword in raw_lower for keyword in ['error', 'alarm', 'fail']):
            response.response_type = 'error'
            # Parse error details
            error_match = self.response_parsers['error'].search(raw_data)
            if error_match:
                response.parsed_data = {
                    'error_type': error_match.group(1),
                    'error_message': error_match.group(2).strip()
                }
        elif raw_data.startswith('<') and raw_data.endswith('>'):
            response.response_type = 'status'
            # Parse GRBL status
            status_match = self.response_parsers['grbl_status'].search(raw_data)
            if status_match:
                status_parts = status_match.group(1).split('|')
                response.parsed_data = {'status': status_parts[0]}
                if len(status_parts) > 1:
                    response.parsed_data['details'] = status_parts[1:]
        elif any(fw in raw_lower for fw in ['grbl', 'marlin', 'repetier', 'smoothie', 'klipper']):
            response.response_type = 'firmware'
            response.parsed_data = {'firmware_info': raw_data}
        
        return response
    
    def _handle_response(self, response: SerialResponse):
        """Handle response for pending commands"""
        # Simple approach: match responses to oldest pending command
        if self.pending_commands:
            # Get oldest pending command
            oldest_id = min(self.pending_commands.keys())
            command_data = self.pending_commands.pop(oldest_id)
            
            # Call callback if provided
            if command_data['callback']:
                try:
                    command_data['callback'](response)
                except Exception as e:
                    self.error_occurred.emit(f"Command callback error: {e}")
    
    def _detect_firmware(self):
        """Attempt to detect connected firmware type"""
        detection_commands = ["M115", "$I", "version", "STATUS"]
        
        for cmd in detection_commands:
            self.send_command(cmd, priority=1, expect_response=True, 
                            callback=self._firmware_detection_callback)
    
    def _firmware_detection_callback(self, response: SerialResponse):
        """Handle firmware detection response"""
        raw_lower = response.raw_data.lower()
        
        if 'grbl' in raw_lower:
            self.connection_info.firmware = FirmwareType.GRBL
            self.firmware_info = {'type': 'GRBL', 'version': response.raw_data}
        elif 'marlin' in raw_lower:
            self.connection_info.firmware = FirmwareType.MARLIN
            self.firmware_info = {'type': 'Marlin', 'version': response.raw_data}
        elif 'repetier' in raw_lower:
            self.connection_info.firmware = FirmwareType.REPETIER
            self.firmware_info = {'type': 'Repetier', 'version': response.raw_data}
        elif 'smoothie' in raw_lower:
            self.connection_info.firmware = FirmwareType.SMOOTHIEWARE
            self.firmware_info = {'type': 'Smoothieware', 'version': response.raw_data}
        elif 'klipper' in raw_lower:
            self.connection_info.firmware = FirmwareType.KLIPPER
            self.firmware_info = {'type': 'Klipper', 'version': response.raw_data}
        else:
            self.connection_info.firmware = FirmwareType.UNKNOWN
            self.firmware_info = {'type': 'Unknown', 'raw_response': response.raw_data}
        
        self.firmware_detected.emit(self.connection_info.firmware, self.firmware_info)
    
    def _schedule_reconnect(self):
        """Schedule automatic reconnection attempt"""
        if not self.auto_reconnect or self.reconnect_attempts >= self.max_reconnect_attempts:
            return
        
        self.reconnect_attempts += 1
        self._update_connection_state(ConnectionState.RECONNECTING)
        
        # Use QTimer for GUI thread safety
        reconnect_timer = QTimer()
        reconnect_timer.timeout.connect(lambda: self._attempt_reconnect(reconnect_timer))
        reconnect_timer.setSingleShot(True)
        reconnect_timer.start(int(self.reconnect_delay * 1000))
    
    def _attempt_reconnect(self, timer):
        """Attempt to reconnect to the last known configuration"""
        timer.deleteLater()
        
        if self.connection_info.port and self.connection_info.baudrate:
            self.connect(self.connection_info.port, self.connection_info.baudrate)
    
    def _periodic_maintenance(self):
        """Periodic maintenance tasks"""
        current_time = time.time()
        
        # Check for command timeouts
        expired_commands = []
        for cmd_id, cmd_data in self.pending_commands.items():
            if current_time - cmd_data['timestamp'] > self.command_timeout:
                expired_commands.append(cmd_id)
        
        for cmd_id in expired_commands:
            cmd_data = self.pending_commands.pop(cmd_id)
            self.response_timeout.emit(cmd_data['command'])
        
        # Heartbeat check
        if (self.is_connected() and 
            current_time - self.last_activity > self.heartbeat_interval):
            # Send heartbeat command based on firmware type
            if self.connection_info.firmware == FirmwareType.GRBL:
                self.send_command("?", priority=1)  # GRBL status query
            elif self.connection_info.firmware == FirmwareType.MARLIN:
                self.send_command("M114", priority=1)  # Marlin position query
        
        # Update connection info
        self.connection_info_updated.emit(self.connection_info)
    
    def cleanup(self):
        """Clean shutdown of serial manager"""
        self.monitor_timer.stop()
        self.disconnect()