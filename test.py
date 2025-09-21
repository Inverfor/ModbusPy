import serial
import struct
# Example Usage:
#ser = serial.Serial(...) # Initialize your serial port
ser = serial.Serial(
    port='COM7',  # or '/dev/ttyUSB0'
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1  # Timeout in seconds
)
def calculate_crc(data):
    # Implement CRC-16 Modbus calculation here
    # This is a placeholder, a full implementation is complex
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if (crc & 0x0001):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little') # Return as bytes

def read_holding_registers(slave_id, start_address, num_registers, ser):
    # Construct the Modbus RTU request frame
    request_data = bytes([slave_id, 0x03, (start_address >> 8) & 0xFF, start_address & 0xFF,
                          (num_registers >> 8) & 0xFF, num_registers & 0xFF])
    crc = calculate_crc(request_data)
    full_request = request_data + crc

    ser.write(full_request)
    response = ser.read(3 + num_registers * 2 + 2) # Slave ID, Function Code, Byte Count, Data, CRC

    if len(response) < (3 + num_registers * 2 + 2):
        print("Incomplete response")
        return None

    # Validate CRC and parse response (simplified)
    received_crc = response[-2:]
    calculated_crc = calculate_crc(response[:-2])

    if received_crc != calculated_crc:
        print("CRC mismatch!")
        return None

    # Extract register values
    registers = []
    for i in range(num_registers):
        value = (response[3 + i * 2] << 8) | response[4 + i * 2]
        registers.append(value)
    return registers

def read_floating_registers(slave_id, start_address, ser):
    registers_raw =  read_holding_registers(slave_id, start_address, 2, ser)
    # Pack the two 16-bit integers into a 32-bit binary string (little-endian word order)
    packed_data = struct.pack('<HH', registers_raw[0], registers_raw[1])
    # Unpack the binary string into a float
    float_value = struct.unpack('<f', packed_data)[0]
    return float_value
registers = read_floating_registers(1, 2014, ser)
if registers:
    print(f"Read registers: {registers}")
ser.close()