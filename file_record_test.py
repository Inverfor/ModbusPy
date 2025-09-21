#!/usr/bin/env python3
"""
Test script for Modbus Function 14h (Read File Records) implementation
This script demonstrates how to use the new file record functionality
"""

import sys
import time
from modbus_gui import ModbusGUI
import tkinter as tk

def test_file_record_functionality():
    """
    Test the file record functionality without actual hardware
    This demonstrates the protocol structure and usage
    """
    print("Modbus Function 14h (Read File Records) Test")
    print("=" * 50)
    
    # Create a test instance (without GUI)
    root = tk.Tk()
    root.withdraw()  # Hide the main window for testing
    
    app = ModbusGUI(root)
    
    # Test parameters
    slave_id = 1
    file_number = 1
    record_number = 0
    record_length = 10
    
    print(f"Test Parameters:")
    print(f"  Slave ID: {slave_id}")
    print(f"  File Number: {file_number}")
    print(f"  Record Number: {record_number}")
    print(f"  Record Length: {record_length}")
    print()
    
    # Demonstrate request frame construction
    print("Modbus Function 14h Request Frame Structure:")
    print("  Byte 0: Slave ID")
    print("  Byte 1: Function Code (0x14)")
    print("  Byte 2: Byte Count (7)")
    print("  Byte 3: Reference Type (6)")
    print("  Bytes 4-5: File Number (Big Endian)")
    print("  Bytes 6-7: Record Number (Big Endian)")
    print("  Bytes 8-9: Record Length (Big Endian)")
    print("  Bytes 10-11: CRC-16 (Little Endian)")
    print()
    
    # Show example request frame
    byte_count = 7
    reference_type = 6
    
    request_data = bytes([
        slave_id,
        0x14,  # Function code 14h
        byte_count,
        reference_type,
        (file_number >> 8) & 0xFF, file_number & 0xFF,
        (record_number >> 8) & 0xFF, record_number & 0xFF,
        (record_length >> 8) & 0xFF, record_length & 0xFF
    ])
    
    crc = app.calculate_crc(request_data)
    full_request = request_data + crc
    
    print("Example Request Frame (Hex):")
    hex_request = ' '.join([f"{byte:02X}" for byte in full_request])
    print(f"  {hex_request}")
    print()
    
    print("Response Frame Structure:")
    print("  Byte 0: Slave ID")
    print("  Byte 1: Function Code (0x14)")
    print("  Byte 2: Response Data Length")
    print("  Byte 3: File Response Length")
    print("  Byte 4: Reference Type")
    print("  Bytes 5-N: File Data")
    print("  Bytes N+1, N+2: CRC-16 (Little Endian)")
    print()
    
    print("Usage Instructions:")
    print("1. Connect to your Modbus RTU device using the Serial Configuration")
    print("2. Set the Slave ID in the Modbus Parameters section")
    print("3. In the File Records section, configure:")
    print("   - File Number: The file identifier on the slave device")
    print("   - Record Number: Starting record within the file (0-based)")
    print("   - Record Length: Number of registers to read")
    print("4. Click 'Read File Records' for hex data or 'Read as Text' for ASCII interpretation")
    print()
    
    print("Common File Record Parameters:")
    print("- File Number: Usually 1-65535 (device specific)")
    print("- Record Number: 0-based index within the file")
    print("- Record Length: Number of 16-bit registers (words) to read")
    print("- Reference Type: Usually 6 (standard file record reference)")
    print()
    
    root.destroy()

if __name__ == "__main__":
    test_file_record_functionality()
