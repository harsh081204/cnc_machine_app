import os
from core.config_manager import ConfigManager, ActuatorConfig
from core.firmware_utils import FirmwareUtils, FirmwareType
from core.serial_manager import SerialManager

print("=== App Integration Test ===")

# --- Test ConfigManager ---
print("\n[ConfigManager] Testing actuator config save/load...")
config_manager = ConfigManager()

# Add a test actuator
test_actuator = ActuatorConfig(name="TestActuator", command="G55 P0 S1;", enabled=True, description="Test actuator")
config_manager.set_actuator_config("TestActuator", test_actuator)

# Load actuators and check
actuators = config_manager.get_actuator_configs()
assert "TestActuator" in actuators, "TestActuator not found after save!"
print("Actuator configs:", actuators)

# Remove test actuator
config_manager.remove_actuator_config("TestActuator")
print("Actuator removed. Current configs:", config_manager.get_actuator_configs())

# --- Test FirmwareUtils ---
print("\n[FirmwareUtils] Testing firmware detection and info extraction...")
firmware_utils = FirmwareUtils()

# Sample GRBL response
sample_grbl = "Grbl 1.1h ['$' for help]"
fw_type = firmware_utils.detect_firmware_type(sample_grbl)
assert fw_type == FirmwareType.GRBL, f"Expected GRBL, got {fw_type}"
info = firmware_utils.extract_firmware_info(sample_grbl)
print("Detected firmware:", fw_type)
print("Extracted info:", firmware_utils.format_firmware_info(info))

# Sample Marlin response
sample_marlin = "FIRMWARE_NAME:Marlin 2.0.9.3 (Github)"
fw_type2 = firmware_utils.detect_firmware_type(sample_marlin)
assert fw_type2 == FirmwareType.MARLIN, f"Expected MARLIN, got {fw_type2}"
info2 = firmware_utils.extract_firmware_info(sample_marlin)
print("Detected firmware:", fw_type2)
print("Extracted info:", firmware_utils.format_firmware_info(info2))

# --- Test SerialManager (mocked) ---
print("\n[SerialManager] Testing instantiation and port listing (mocked)...")
serial_manager = SerialManager(auto_reconnect=False)
try:
    ports = serial_manager.get_available_ports()
    print("Available ports:", ports)
except Exception as e:
    print("SerialManager port listing failed (expected if no hardware):", e)

print("\n[SerialManager] Testing connect/disconnect (mocked, expect failure if no hardware)...")
try:
    # Use a likely-nonexistent port for safety
    result = serial_manager.connect(port_name="COM_FAKE", baudrate=115200)
    print("Connect result (should be False):", result)
    serial_manager.disconnect()
    print("Disconnect called.")
except Exception as e:
    print("SerialManager connect/disconnect failed (expected if no hardware):", e)

print("\n=== Integration Test Complete ===") 