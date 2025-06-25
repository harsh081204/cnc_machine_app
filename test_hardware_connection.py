#!/usr/bin/env python3
"""
Hardware connection test script for SerialManager
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QEventLoop
from core.firmware_utils import FirmwareUtils

def test_hardware_connection():
    """Test actual hardware connection"""
    print("🔌 Testing Hardware Connection...")
    
    try:
        from core.serial_manager import SerialManager, ConnectionState
        from core.firmware_utils import FirmwareType
        
        # Create SerialManager and FirmwareUtils
        manager = SerialManager(auto_reconnect=False, command_timeout=3.0)
        firmware_utils = FirmwareUtils()
        
        # Get available ports
        ports = manager.get_available_ports()
        print(f"\n📋 Available ports ({len(ports)}):")
        
        if not ports:
            print("❌ No serial ports found!")
            print("💡 Make sure your CNC controller is connected via USB")
            return False
        
        for i, port_info in enumerate(ports):
            port_name, description, hwid = port_info
            print(f"   {i+1}. {port_name}: {description}")
            print(f"      Hardware ID: {hwid}")
        
        # Ask user to select a port
        if len(ports) == 1:
            selected_port = ports[0]
            print(f"\n🔗 Auto-selecting the only available port: {selected_port[0]}")
        else:
            try:
                choice = input(f"\n🔗 Select port (1-{len(ports)}): ")
                port_index = int(choice) - 1
                if 0 <= port_index < len(ports):
                    selected_port = ports[port_index]
                else:
                    print("❌ Invalid selection")
                    return False
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Cancelled")
                return False
        
        port_name, description, hwid = selected_port
        print(f"\n🔗 Attempting to connect to: {port_name}")
        print(f"📝 Description: {description}")
        
        # Try to detect firmware type first with default settings
        print("\n🔍 Attempting firmware detection...")
        success = manager.connect(
            port_name=port_name,
            baudrate=115200,
            timeout=2.0,
            write_timeout=2.0
        )
        
        if success:
            print("✅ Initial connection established!")
            
            # Wait a moment for firmware detection
            time.sleep(1)
            
            # Get connection info
            info = manager.get_connection_info()
            firmware_type = info.firmware
            
            # Get suggested settings if firmware was detected
            if firmware_type != FirmwareType.UNKNOWN:
                print(f"\n✨ Detected {firmware_type.value} firmware!")
                suggested_settings = firmware_utils.suggest_connection_settings(firmware_type)
                
                # If current settings differ from suggested, reconnect with suggested settings
                if suggested_settings['baudrate'] != 115200:
                    print(f"\n🔄 Reconnecting with suggested settings for {firmware_type.value}...")
                    manager.disconnect()
                    success = manager.connect(
                        port_name=port_name,
                        baudrate=suggested_settings['baudrate'],
                        timeout=suggested_settings['timeout'],
                        write_timeout=suggested_settings['timeout'],
                        xonxoff=suggested_settings['flow_control'],
                        rtscts=suggested_settings['flow_control']
                    )
                    if not success:
                        print("⚠️ Failed to connect with suggested settings, reverting to defaults...")
                        success = manager.connect(
                            port_name=port_name,
                            baudrate=115200,
                            timeout=2.0,
                            write_timeout=2.0
                        )
            
            # Get final connection info
            info = manager.get_connection_info()
            print(f"\n📊 Connection Info:")
            print(f"   Port: {info.port}")
            print(f"   Baudrate: {info.baudrate}")
            print(f"   Firmware: {info.firmware.value}")
            print(f"   State: {info.state.value}")
            print(f"   Bytes sent: {info.bytes_sent}")
            print(f"   Bytes received: {info.bytes_received}")
            
            # Test sending a simple command based on firmware type
            print(f"\n📤 Testing command sending...")
            test_commands = {
                FirmwareType.GRBL: ["$I", "$$"],
                FirmwareType.MARLIN: ["M115", "M503"],
                FirmwareType.REPETIER: ["M115", "M205"],
                FirmwareType.SMOOTHIEWARE: ["version", "config"],
                FirmwareType.KLIPPER: ["STATUS", "HELP"],
                FirmwareType.UNKNOWN: ["M115"]  # Fallback command
            }
            
            commands = test_commands.get(info.firmware, ["M115"])
            for cmd in commands:
                print(f"   Sending: {cmd}")
                command_id = manager.send_command(cmd, priority=1)
                
                if command_id:
                    print(f"   ✅ Command sent with ID: {command_id}")
                    time.sleep(2)  # Wait for response
                    
                    if info.responses_received > 0:
                        print("   ✅ Response received!")
                    else:
                        print("   ⚠️  No response received (this might be normal)")
                else:
                    print("   ❌ Failed to send command")
            
            # Disconnect
            print(f"\n🔌 Disconnecting...")
            manager.disconnect()
            print("✅ Disconnected")
            
        else:
            print("❌ Failed to connect!")
            print("💡 Possible issues:")
            print("   - Wrong baudrate")
            print("   - Port is in use by another application")
            print("   - Device not powered on")
            print("   - Driver issues")
            print("\n🔍 Running baudrate scan to help diagnose...")
            return test_baudrate_scan()
        
        return success
        
    except Exception as e:
        print(f"❌ Error during hardware test: {e}")
        return False

def test_baudrate_scan():
    """Test different baudrates with progress indicators"""
    print("\n🔍 Baudrate Scan Test...")
    
    try:
        from core.serial_manager import SerialManager
        from core.firmware_utils import FirmwareUtils
        
        # Get available ports
        manager = SerialManager(auto_reconnect=False, command_timeout=1.0)
        firmware_utils = FirmwareUtils()
        ports = manager.get_available_ports()
        
        if not ports:
            print("❌ No ports available for baudrate scan")
            return False
        
        port_name = ports[0][0]  # Use first available port
        baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 250000]
        total_baudrates = len(baudrates)
        
        print(f"🔍 Scanning baudrates for {port_name}...")
        print("Progress: ", end="", flush=True)
        
        found_working_config = False
        best_baudrate = None
        best_firmware = None
        
        for i, baudrate in enumerate(baudrates, 1):
            print(f"\rProgress: [{'=' * i}{' ' * (total_baudrates - i)}] {i}/{total_baudrates} ", end="", flush=True)
            
            try:
                success = manager.connect(
                    port_name=port_name,
                    baudrate=baudrate,
                    timeout=1.0,
                    write_timeout=1.0
                )
                
                if success:
                    print(f"\n   Testing {baudrate} baud... ✅")
                    
                    # Try firmware detection commands
                    test_commands = ["M115", "$I", "version", "STATUS"]
                    for cmd in test_commands:
                        manager.send_command(cmd, priority=1)
                        time.sleep(0.5)
                    
                    info = manager.get_connection_info()
                    if info.responses_received > 0:
                        print(f"      📡 Response received at {baudrate} baud")
                        if info.firmware != FirmwareType.UNKNOWN:
                            print(f"      ✨ Detected {info.firmware.value} firmware!")
                            best_baudrate = baudrate
                            best_firmware = info.firmware
                            found_working_config = True
                            
                    manager.disconnect()
                    
                else:
                    print(f"\n   Testing {baudrate} baud... ❌")
                    
            except Exception as e:
                print(f"\n   Testing {baudrate} baud... ❌ ({str(e)})")
        
        print("\n")  # New line after progress bar
        
        if found_working_config:
            print(f"✅ Found working configuration:")
            print(f"   Baudrate: {best_baudrate}")
            print(f"   Firmware: {best_firmware.value}")
            
            # Get suggested settings
            if best_firmware:
                suggested = firmware_utils.suggest_connection_settings(best_firmware)
                if suggested['baudrate'] != best_baudrate:
                    print(f"\n💡 Note: {best_firmware.value} typically uses {suggested['baudrate']} baud")
                    print(f"   You may want to try that rate for optimal performance")
        else:
            print("❌ No working configuration found")
            print("💡 Troubleshooting tips:")
            print("   - Check if device is powered on")
            print("   - Try a different USB cable")
            print("   - Check if drivers are installed")
            print("   - Some devices may need specific timing/settings")
        
        return found_working_config
        
    except Exception as e:
        print(f"❌ Error during baudrate scan: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Hardware Connection Test\n")
    
    # Create QApplication for Qt functionality
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Test 1: Hardware connection
    success1 = test_hardware_connection()
    
    # Test 2: Baudrate scan (if first test failed)
    if not success1:
        print("\n" + "="*50)
        success2 = test_baudrate_scan()
    
    print("\n" + "="*50)
    print("📋 Test Summary:")
    print(f"   Hardware connection: {'✅ PASS' if success1 else '❌ FAIL'}")
    if not success1:
        print(f"   Baudrate scan: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    print("\n💡 Troubleshooting tips:")
    print("   - Ensure your CNC controller is powered on")
    print("   - Check USB cable connection")
    print("   - Try different USB ports")
    print("   - Install proper USB drivers if needed")
    print("   - Check if another application is using the port")
    print("   - Some devices may need specific timing/settings")
    print("   - Check device documentation for correct baudrate")
    
    return success1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 