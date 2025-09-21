import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import struct
import threading
import time

class ModbusGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus RTU Reader - GUI Interface")
        self.root.geometry("800x600")
        
        # Serial connection
        self.ser = None
        self.is_connected = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Serial Configuration Frame
        config_frame = ttk.LabelFrame(main_frame, text="Serial Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Port
        ttk.Label(config_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.port_var = tk.StringVar(value="COM7")
        port_entry = ttk.Entry(config_frame, textvariable=self.port_var, width=15)
        port_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Baudrate
        ttk.Label(config_frame, text="Baudrate:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_combo = ttk.Combobox(config_frame, textvariable=self.baudrate_var, 
                                     values=["9600", "19200", "38400", "57600", "115200"], width=12)
        baudrate_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Timeout
        ttk.Label(config_frame, text="Timeout (s):").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.timeout_var = tk.StringVar(value="1")
        timeout_entry = ttk.Entry(config_frame, textvariable=self.timeout_var, width=8)
        timeout_entry.grid(row=0, column=5, sticky=tk.W)
        
        # Connection buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=1, column=0, columnspan=6, pady=(10, 0))
        
        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self.connect_serial)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_serial, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT)
        
        # Connection status
        self.status_var = tk.StringVar(value="Disconnected")
        status_label = ttk.Label(button_frame, textvariable=self.status_var, foreground="red")
        status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Modbus Parameters Frame
        modbus_frame = ttk.LabelFrame(main_frame, text="Modbus Parameters", padding="10")
        modbus_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Slave ID
        ttk.Label(modbus_frame, text="Slave ID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.slave_id_var = tk.StringVar(value="1")
        slave_id_entry = ttk.Entry(modbus_frame, textvariable=self.slave_id_var, width=10)
        slave_id_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Start Address
        ttk.Label(modbus_frame, text="Start Address:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.start_addr_var = tk.StringVar(value="2014")
        start_addr_entry = ttk.Entry(modbus_frame, textvariable=self.start_addr_var, width=10)
        start_addr_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Number of Registers
        ttk.Label(modbus_frame, text="Num Registers:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.num_regs_var = tk.StringVar(value="2")
        num_regs_entry = ttk.Entry(modbus_frame, textvariable=self.num_regs_var, width=10)
        num_regs_entry.grid(row=0, column=5, sticky=tk.W)
        
        # Read buttons
        read_frame = ttk.Frame(modbus_frame)
        read_frame.grid(row=1, column=0, columnspan=6, pady=(10, 0))
        
        self.read_holding_btn = ttk.Button(read_frame, text="Read Holding Registers", 
                                          command=self.read_holding_registers, state=tk.DISABLED)
        self.read_holding_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.read_float_btn = ttk.Button(read_frame, text="Read Float Value", 
                                        command=self.read_float_value, state=tk.DISABLED)
        self.read_float_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.continuous_btn = ttk.Button(read_frame, text="Start Continuous Read", 
                                        command=self.toggle_continuous_read, state=tk.DISABLED)
        self.continuous_btn.pack(side=tk.LEFT)
        
        # File Records Frame (Function Code 14h)
        file_frame = ttk.LabelFrame(main_frame, text="File Records (Function 14h)", padding="10")
        file_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # File Number
        ttk.Label(file_frame, text="File Number:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.file_number_var = tk.StringVar(value="1")
        file_number_entry = ttk.Entry(file_frame, textvariable=self.file_number_var, width=10)
        file_number_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Record Number
        ttk.Label(file_frame, text="Record Number:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.record_number_var = tk.StringVar(value="0")
        record_number_entry = ttk.Entry(file_frame, textvariable=self.record_number_var, width=10)
        record_number_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Record Length
        ttk.Label(file_frame, text="Record Length:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.record_length_var = tk.StringVar(value="10")
        record_length_entry = ttk.Entry(file_frame, textvariable=self.record_length_var, width=10)
        record_length_entry.grid(row=0, column=5, sticky=tk.W)
        
        # File Records buttons
        file_read_frame = ttk.Frame(file_frame)
        file_read_frame.grid(row=1, column=0, columnspan=6, pady=(10, 0))
        
        self.read_file_btn = ttk.Button(file_read_frame, text="Read File Records", 
                                       command=self.read_file_records, state=tk.DISABLED)
        self.read_file_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.read_file_as_text_btn = ttk.Button(file_read_frame, text="Read as Text", 
                                               command=self.read_file_as_text, state=tk.DISABLED)
        self.read_file_as_text_btn.pack(side=tk.LEFT)
        
        # Results Frame
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=80)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear button
        clear_btn = ttk.Button(results_frame, text="Clear Results", command=self.clear_results)
        clear_btn.grid(row=1, column=0, pady=(5, 0))
        
        # Continuous reading variables
        self.continuous_reading = False
        self.continuous_thread = None
        
    def calculate_crc(self, data):
        """Calculate CRC-16 Modbus"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if (crc & 0x0001):
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, 'little')
    
    def connect_serial(self):
        """Connect to serial port"""
        try:
            port = self.port_var.get()
            baudrate = int(self.baudrate_var.get())
            timeout = float(self.timeout_var.get())
            
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            
            self.is_connected = True
            self.status_var.set("Connected")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.read_holding_btn.config(state=tk.NORMAL)
            self.read_float_btn.config(state=tk.NORMAL)
            self.continuous_btn.config(state=tk.NORMAL)
            self.read_file_btn.config(state=tk.NORMAL)
            self.read_file_as_text_btn.config(state=tk.NORMAL)
            
            self.log_message(f"Connected to {port} at {baudrate} baud")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.log_message(f"Connection failed: {str(e)}")
    
    def disconnect_serial(self):
        """Disconnect from serial port"""
        try:
            if self.continuous_reading:
                self.toggle_continuous_read()
            
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            self.is_connected = False
            self.status_var.set("Disconnected")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.read_holding_btn.config(state=tk.DISABLED)
            self.read_float_btn.config(state=tk.DISABLED)
            self.continuous_btn.config(state=tk.DISABLED)
            self.read_file_btn.config(state=tk.DISABLED)
            self.read_file_as_text_btn.config(state=tk.DISABLED)
            
            self.log_message("Disconnected from serial port")
            
        except Exception as e:
            messagebox.showerror("Disconnection Error", f"Failed to disconnect: {str(e)}")
    
    def read_holding_registers_raw(self, slave_id, start_address, num_registers):
        """Read holding registers from Modbus device"""
        if not self.is_connected or not self.ser:
            return None
        
        try:
            # Construct the Modbus RTU request frame
            request_data = bytes([slave_id, 0x03, (start_address >> 8) & 0xFF, start_address & 0xFF,
                                  (num_registers >> 8) & 0xFF, num_registers & 0xFF])
            crc = self.calculate_crc(request_data)
            full_request = request_data + crc

            self.ser.write(full_request)
            response = self.ser.read(3 + num_registers * 2 + 2)

            if len(response) < (3 + num_registers * 2 + 2):
                self.log_message("Incomplete response received")
                return None

            # Validate CRC
            received_crc = response[-2:]
            calculated_crc = self.calculate_crc(response[:-2])

            if received_crc != calculated_crc:
                self.log_message("CRC mismatch!")
                return None

            # Extract register values
            registers = []
            for i in range(num_registers):
                value = (response[3 + i * 2] << 8) | response[4 + i * 2]
                registers.append(value)
            return registers
            
        except Exception as e:
            self.log_message(f"Error reading registers: {str(e)}")
            return None
    
    def read_holding_registers(self):
        """Read holding registers and display results"""
        try:
            slave_id = int(self.slave_id_var.get())
            start_address = int(self.start_addr_var.get())
            num_registers = int(self.num_regs_var.get())
            
            registers = self.read_holding_registers_raw(slave_id, start_address, num_registers)
            
            if registers:
                timestamp = time.strftime("%H:%M:%S")
                self.log_message(f"[{timestamp}] Read {num_registers} registers from address {start_address}:")
                for i, value in enumerate(registers):
                    self.log_message(f"  Register {start_address + i}: {value} (0x{value:04X})")
            else:
                self.log_message("Failed to read holding registers")
                
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numeric values")
        except Exception as e:
            messagebox.showerror("Read Error", f"Error reading registers: {str(e)}")
    
    def read_float_value(self):
        """Read floating point value from two consecutive registers"""
        try:
            slave_id = int(self.slave_id_var.get())
            start_address = int(self.start_addr_var.get())
            
            registers_raw = self.read_holding_registers_raw(slave_id, start_address, 2)
            
            if registers_raw and len(registers_raw) >= 2:
                # Pack the two 16-bit integers into a 32-bit binary string (little-endian word order)
                packed_data = struct.pack('<HH', registers_raw[0], registers_raw[1])
                # Unpack the binary string into a float
                float_value = struct.unpack('<f', packed_data)[0]
                
                timestamp = time.strftime("%H:%M:%S")
                self.log_message(f"[{timestamp}] Float value from address {start_address}: {float_value:.6f}")
                self.log_message(f"  Raw registers: {registers_raw[0]} (0x{registers_raw[0]:04X}), {registers_raw[1]} (0x{registers_raw[1]:04X})")
            else:
                self.log_message("Failed to read float value")
                
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numeric values")
        except Exception as e:
            messagebox.showerror("Read Error", f"Error reading float value: {str(e)}")
    
    def toggle_continuous_read(self):
        """Toggle continuous reading mode"""
        if not self.continuous_reading:
            self.continuous_reading = True
            self.continuous_btn.config(text="Stop Continuous Read")
            self.continuous_thread = threading.Thread(target=self.continuous_read_worker, daemon=True)
            self.continuous_thread.start()
            self.log_message("Started continuous reading...")
        else:
            self.continuous_reading = False
            self.continuous_btn.config(text="Start Continuous Read")
            self.log_message("Stopped continuous reading")
    
    def continuous_read_worker(self):
        """Worker thread for continuous reading"""
        while self.continuous_reading and self.is_connected:
            try:
                slave_id = int(self.slave_id_var.get())
                start_address = int(self.start_addr_var.get())
                
                registers_raw = self.read_holding_registers_raw(slave_id, start_address, 2)
                
                if registers_raw and len(registers_raw) >= 2:
                    packed_data = struct.pack('<HH', registers_raw[0], registers_raw[1])
                    float_value = struct.unpack('<f', packed_data)[0]
                    
                    timestamp = time.strftime("%H:%M:%S")
                    self.root.after(0, lambda: self.log_message(f"[{timestamp}] Continuous: {float_value:.6f}"))
                
                time.sleep(1)  # Read every second
                
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"Continuous read error: {str(e)}"))
                break
    
    def read_file_records_raw(self, slave_id, file_number, record_number, record_length):
        """Read file records using Modbus function code 14h (0x14)"""
        if not self.is_connected or not self.ser:
            return None
        
        try:
            # Construct the Modbus RTU request frame for function 14h
            # Format: [Slave ID][Function Code 14h][Byte Count][Reference Type][File Number][Record Number][Record Length]
            byte_count = 7  # Reference Type (1) + File Number (2) + Record Number (2) + Record Length (2)
            reference_type = 6  # Standard reference type for file records
            
            request_data = bytes([
                slave_id,
                0x14,  # Function code 14h (Read File Record)
                byte_count,
                reference_type,
                (file_number >> 8) & 0xFF, file_number & 0xFF,
                (record_number >> 8) & 0xFF, record_number & 0xFF,
                (record_length >> 8) & 0xFF, record_length & 0xFF
            ])
            
            crc = self.calculate_crc(request_data)
            full_request = request_data + crc
            
            # Send request
            self.ser.write(full_request)
            
            # Read response header first (Slave ID + Function Code + Response Data Length)
            header_response = self.ser.read(3)
            if len(header_response) < 3:
                self.log_message("Incomplete header response received")
                return None
            
            response_data_length = header_response[2]
            
            # Read the rest of the response (data + CRC)
            remaining_response = self.ser.read(response_data_length + 2)
            if len(remaining_response) < (response_data_length + 2):
                self.log_message("Incomplete response data received")
                return None
            
            full_response = header_response + remaining_response
            
            # Validate CRC
            received_crc = full_response[-2:]
            calculated_crc = self.calculate_crc(full_response[:-2])
            
            if received_crc != calculated_crc:
                self.log_message("CRC mismatch in file record response!")
                return None
            
            # Extract file record data
            # Response format: [Slave ID][Function Code][Response Data Length][File Response Length][Reference Type][Data...]
            if len(full_response) < 6:
                self.log_message("Response too short for file record data")
                return None
            
            file_response_length = full_response[3]
            file_reference_type = full_response[4]
            
            # Extract the actual data (skip header bytes)
            data_start_index = 5
            data_end_index = data_start_index + (file_response_length - 1)  # -1 because file_response_length includes reference type
            
            if data_end_index > len(full_response) - 2:  # -2 for CRC
                self.log_message("Data length exceeds response size")
                return None
            
            file_data = full_response[data_start_index:data_end_index]
            
            return {
                'file_number': file_number,
                'record_number': record_number,
                'record_length': record_length,
                'reference_type': file_reference_type,
                'data': file_data
            }
            
        except Exception as e:
            self.log_message(f"Error reading file records: {str(e)}")
            return None
    
    def read_file_records(self):
        """Read file records and display results as hex data"""
        try:
            slave_id = int(self.slave_id_var.get())
            file_number = int(self.file_number_var.get())
            record_number = int(self.record_number_var.get())
            record_length = int(self.record_length_var.get())
            
            result = self.read_file_records_raw(slave_id, file_number, record_number, record_length)
            
            if result:
                timestamp = time.strftime("%H:%M:%S")
                self.log_message(f"[{timestamp}] File Record Read (Function 14h):")
                self.log_message(f"  File Number: {result['file_number']}")
                self.log_message(f"  Record Number: {result['record_number']}")
                self.log_message(f"  Record Length: {result['record_length']}")
                self.log_message(f"  Reference Type: {result['reference_type']}")
                self.log_message(f"  Data Length: {len(result['data'])} bytes")
                
                # Display data as hex
                hex_data = ' '.join([f"{byte:02X}" for byte in result['data']])
                self.log_message(f"  Hex Data: {hex_data}")
                
                # Display data as 16-bit words (big-endian)
                if len(result['data']) >= 2:
                    words = []
                    for i in range(0, len(result['data']) - 1, 2):
                        word = (result['data'][i] << 8) | result['data'][i + 1]
                        words.append(word)
                    self.log_message(f"  Words: {words}")
                
            else:
                self.log_message("Failed to read file records")
                
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numeric values")
        except Exception as e:
            messagebox.showerror("Read Error", f"Error reading file records: {str(e)}")
    
    def read_file_as_text(self):
        """Read file records and display results as text"""
        try:
            slave_id = int(self.slave_id_var.get())
            file_number = int(self.file_number_var.get())
            record_number = int(self.record_number_var.get())
            record_length = int(self.record_length_var.get())
            
            result = self.read_file_records_raw(slave_id, file_number, record_number, record_length)
            
            if result:
                timestamp = time.strftime("%H:%M:%S")
                self.log_message(f"[{timestamp}] File Record as Text (Function 14h):")
                self.log_message(f"  File Number: {result['file_number']}")
                self.log_message(f"  Record Number: {result['record_number']}")
                self.log_message(f"  Record Length: {result['record_length']}")
                
                # Try to decode as ASCII text
                try:
                    text_data = result['data'].decode('ascii', errors='replace')
                    # Remove null characters and non-printable characters for cleaner display
                    clean_text = ''.join(char if char.isprintable() else '.' for char in text_data)
                    self.log_message(f"  Text Data: '{clean_text}'")
                except Exception as decode_error:
                    self.log_message(f"  Text decode error: {str(decode_error)}")
                    # Fallback to hex display
                    hex_data = ' '.join([f"{byte:02X}" for byte in result['data']])
                    self.log_message(f"  Hex Data: {hex_data}")
                
                # Also show raw bytes for reference
                self.log_message(f"  Raw bytes: {list(result['data'])}")
                
            else:
                self.log_message("Failed to read file records as text")
                
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numeric values")
        except Exception as e:
            messagebox.showerror("Read Error", f"Error reading file records as text: {str(e)}")
    
    def log_message(self, message):
        """Add message to results text area"""
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.see(tk.END)
    
    def clear_results(self):
        """Clear the results text area"""
        self.results_text.delete(1.0, tk.END)
    
    def on_closing(self):
        """Handle window closing"""
        if self.continuous_reading:
            self.toggle_continuous_read()
        if self.is_connected:
            self.disconnect_serial()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ModbusGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
