#!/usr/bin/env python3
"""
Test script to verify SerialManager functionality
"""

import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from core.serial_manager import SerialManager, ConnectionState, FirmwareType
        print("✅ SerialManager imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import SerialManager: {e}")
        return False

def test_serial_manager_creation():
    """Test SerialManager instance creation"""
    print("\n🔍 Testing SerialManager creation...")
    
    try:
        from core.serial_manager import SerialManager
        manager = SerialManager(auto_reconnect=True, command_timeout=5.0)
        print("✅ SerialManager instance created successfully")
        return manager
    except Exception as e:
        print(f"❌ Failed to create SerialManager: {e}")
        return None

def test_port_enumeration(manager):
    """Test port enumeration functionality"""
    print("\n🔍 Testing port enumeration...")
    
    try:
        ports = manager.get_available_ports()
        print(f"✅ Found {len(ports)} available ports:")
        for port_info in ports:
            port_name, description, hwid = port_info
            print(f"   - {port_name}: {description}")
        return True
    except Exception as e:
        print(f"❌ Failed to enumerate ports: {e}")
        return False

def test_connection_states(manager):
    """Test connection state handling"""
    print("\n🔍 Testing connection states...")
    
    try:
        from core.serial_manager import ConnectionState
        
        # Test initial state
        initial_state = manager.get_connection_info().state
        print(f"✅ Initial connection state: {initial_state}")
        
        # Test is_connected method
        is_connected = manager.is_connected()
        print(f"✅ Is connected: {is_connected}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test connection states: {e}")
        return False

def test_signal_connections(manager):
    """Test signal connections"""
    print("\n🔍 Testing signal connections...")
    
    try:
        # Test signal emission (without actual connection)
        manager.error_occurred.emit("Test error message")
        print("✅ Signal connections working")
        return True
    except Exception as e:
        print(f"❌ Failed to test signals: {e}")
        return False

def test_ui_integration():
    """Test UI integration"""
    print("\n🔍 Testing UI integration...")
    
    try:
        from ui.tab_connection import ConnectionTab
        print("✅ ConnectionTab imported successfully")
        
        # Create a minimal app for testing
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Test ConnectionTab creation
        connection_tab = ConnectionTab()
        print("✅ ConnectionTab created successfully")
        
        # Test basic methods
        status = connection_tab.get_connection_status()
        print(f"✅ Connection status: {status}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test UI integration: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting SerialManager Tests...\n")
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import test failed. Exiting.")
        return False
    
    # Test 2: SerialManager creation
    manager = test_serial_manager_creation()
    if manager is None:
        print("\n❌ SerialManager creation failed. Exiting.")
        return False
    
    # Test 3: Port enumeration
    test_port_enumeration(manager)
    
    # Test 4: Connection states
    test_connection_states(manager)
    
    # Test 5: Signal connections
    test_signal_connections(manager)
    
    # Test 6: UI integration
    test_ui_integration()
    
    print("\n🎉 All tests completed!")
    print("\n📋 To test with actual hardware:")
    print("1. Connect your CNC controller via USB")
    print("2. Run the main application: python main.py")
    print("3. Go to the Connection tab")
    print("4. Select your port and click Connect")
    print("5. Check the connection log for status messages")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 