# Modbus RTU GUI - File Records (Function 14h) Implementation

## Overview

This enhanced version of the Modbus RTU GUI now supports **Modbus Function Code 14h (Read File Records)**, which allows reading file data from RTU slave devices. This functionality is particularly useful for accessing configuration files, log files, or other structured data stored on Modbus devices.

## New Features

### File Records Section
The GUI now includes a dedicated "File Records (Function 14h)" section with the following controls:

- **File Number**: Specifies which file to read from (1-65535, device-specific)
- **Record Number**: Starting record within the file (0-based index)
- **Record Length**: Number of 16-bit registers (words) to read
- **Read File Records**: Reads data and displays as hexadecimal values
- **Read as Text**: Reads data and attempts ASCII text interpretation

## Technical Implementation

### Modbus Function 14h Protocol

The implementation follows the standard Modbus specification for Function Code 14h:

**Request Frame Structure:**
```
Byte 0: Slave ID
Byte 1: Function Code (0x14)
Byte 2: Byte Count (7)
Byte 3: Reference Type (6 - standard file record reference)
Bytes 4-5: File Number (Big Endian)
Bytes 6-7: Record Number (Big Endian)
Bytes 8-9: Record Length (Big Endian)
Bytes 10-11: CRC-16 (Little Endian)
```

**Response Frame Structure:**
```
Byte 0: Slave ID
Byte 1: Function Code (0x14)
Byte 2: Response Data Length
Byte 3: File Response Length
Byte 4: Reference Type
Bytes 5-N: File Data
Bytes N+1, N+2: CRC-16 (Little Endian)
```

### Key Methods Added

1. **`read_file_records_raw()`**: Core method that handles the Modbus 14h protocol
2. **`read_file_records()`**: Displays file data as hexadecimal values and 16-bit words
3. **`read_file_as_text()`**: Interprets file data as ASCII text with fallback to hex

## Usage Instructions

### Step 1: Serial Connection
1. Configure your serial port settings (Port, Baudrate, Timeout)
2. Click "Connect" to establish communication

### Step 2: Basic Parameters
1. Set the **Slave ID** of your target device
2. Configure file record parameters:
   - **File Number**: The file identifier on the slave device
   - **Record Number**: Starting position within the file (usually 0)
   - **Record Length**: How many registers to read

### Step 3: Read File Data
- Click **"Read File Records"** for raw hex data display
- Click **"Read as Text"** for ASCII text interpretation

## Example Usage

### Reading Configuration File
```
File Number: 1
Record Number: 0
Record Length: 20
```

### Reading Log Entries
```
File Number: 2
Record Number: 10
Record Length: 50
```

## Output Formats

### Hex Data Output
```
[09:30:15] File Record Read (Function 14h):
  File Number: 1
  Record Number: 0
  Record Length: 10
  Reference Type: 6
  Data Length: 20 bytes
  Hex Data: 48 65 6C 6C 6F 20 57 6F 72 6C 64 00 00 00 00 00 00 00 00 00
  Words: [18533, 27756, 28416, 29295, 25600, 0, 0, 0, 0, 0]
```

### Text Data Output
```
[09:30:20] File Record as Text (Function 14h):
  File Number: 1
  Record Number: 0
  Record Length: 10
  Text Data: 'Hello World.........'
  Raw bytes: [72, 101, 108, 108, 111, 32, 87, 111, 114, 108, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

## Error Handling

The implementation includes comprehensive error handling:

- **Connection Validation**: Ensures serial connection is active
- **CRC Verification**: Validates response integrity
- **Response Length Checks**: Prevents buffer overruns
- **Timeout Handling**: Manages communication timeouts
- **Data Validation**: Checks response format compliance

## Device Compatibility

This implementation should work with any Modbus RTU device that supports Function Code 14h, including:

- Industrial PLCs with file storage capabilities
- Data loggers with historical data files
- Configuration management systems
- Custom Modbus devices with file-based data storage

## Testing

Use the included `file_record_test.py` script to:
- Understand the protocol structure
- See example request frames
- Learn about parameter configuration
- Test without hardware connection

```bash
python file_record_test.py
```

## Troubleshooting

### Common Issues

1. **"Incomplete response received"**
   - Check device supports Function 14h
   - Verify file number exists on device
   - Ensure record number is within file bounds

2. **"CRC mismatch"**
   - Check serial connection quality
   - Verify baudrate and parity settings
   - Ensure proper cable shielding

3. **"Response too short"**
   - Device may not support requested file/record
   - Check device documentation for valid ranges

### Device-Specific Notes

- File numbers and record structures are device-specific
- Consult your device manual for supported file numbers
- Some devices may use different reference types
- Record length limits vary by device manufacturer

## Files Modified

- **`modbus_gui.py`**: Main GUI application with Function 14h support
- **`file_record_test.py`**: Test and demonstration script
- **`README_File_Records.md`**: This documentation file

## Future Enhancements

Potential improvements for future versions:
- Support for multiple file record requests in single transaction
- File write capabilities (Function 15h)
- Automatic file structure detection
- Data export functionality
- Enhanced text encoding support (UTF-8, etc.)
