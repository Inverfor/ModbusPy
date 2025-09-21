#!/usr/bin/env python3
"""
Modbus RTU Industrial Server for Raspberry Pi Zero 2W
Optimized for industrial applications with robust error handling,
logging, and performance optimization for ARM Cortex-A53 architecture.

Features:
- Multi-slave RTU server support
- Industrial-grade logging and diagnostics
- Automatic reconnection and error recovery
- Memory-optimized for 512MB RAM
- Thread-safe operations
- Configuration file support
- Real-time monitoring and statistics
"""

import serial
import struct
import threading
import time
import json
import logging
import queue
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

# Configuration for Pi Zero 2W optimization
PI_ZERO_CONFIG = {
    'max_threads': 4,  # Quad-core ARM Cortex-A53
    'memory_limit_mb': 400,  # Leave 112MB for system
    'cpu_threshold': 80,  # CPU usage threshold
    'max_connections': 10,  # Concurrent connections
    'buffer_size': 1024,  # Serial buffer size
    'response_timeout': 5.0,  # Response timeout
    'reconnect_delay': 2.0,  # Reconnection delay
}

@dataclass
class ModbusRegister:
    """Modbus register data structure"""
    address: int
    value: int
    timestamp: float
    quality: str = "GOOD"  # GOOD, BAD, UNCERTAIN

@dataclass
class SlaveConfig:
    """Slave device configuration"""
    slave_id: int
    name: str
    description: str
    holding_registers: Dict[int, int]
    input_registers: Dict[int, int]
    coils: Dict[int, bool]
    discrete_inputs: Dict[int, bool]
    file_records: Dict[int, Dict[int, bytes]]

@dataclass
class ConnectionStats:
    """Connection statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_request_time: float = 0
    connection_uptime: float = 0
    bytes_sent: int = 0
    bytes_received: int = 0

class ModbusIndustrialServer:
    """Industrial Modbus RTU Server optimized for Raspberry Pi Zero 2W"""
    
    def __init__(self, config_file: str = "modbus_server_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.slaves: Dict[int, SlaveConfig] = {}
        self.stats: Dict[int, ConnectionStats] = {}
        
        # Serial connection
        self.serial_port: Optional[serial.Serial] = None
        self.is_running = False
        self.server_thread: Optional[threading.Thread] = None
        
        # Thread management
        self.executor = ThreadPoolExecutor(max_workers=PI_ZERO_CONFIG['max_threads'])
        self.request_queue = queue.Queue(maxsize=100)
        
        # Logging setup
        self._setup_logging()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Modbus Industrial Server initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load server configuration from JSON file"""
        default_config = {
            "serial": {
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": 1.0
            },
            "server": {
                "max_slaves": 10,
                "log_level": "INFO",
                "log_file": "/var/log/modbus_server.log",
                "stats_interval": 60,
                "backup_interval": 300
            },
            "performance": {
                "memory_check_interval": 30,
                "cpu_check_interval": 10,
                "auto_optimize": True
            }
        }
        
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                return config
            else:
                # Create default config file
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return default_config
    
    def _setup_logging(self):
        """Setup industrial-grade logging"""
        log_level = getattr(logging, self.config['server']['log_level'].upper())
        log_file = self.config['server']['log_file']
        
        # Create log directory if it doesn't exist
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('ModbusServer')
        
        # Add rotation to prevent log files from growing too large
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(file_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_server()
        sys.exit(0)
    
    def add_slave(self, slave_config: SlaveConfig):
        """Add a slave device to the server"""
        if len(self.slaves) >= self.config['server']['max_slaves']:
            raise ValueError(f"Maximum number of slaves ({self.config['server']['max_slaves']}) reached")
        
        self.slaves[slave_config.slave_id] = slave_config
        self.stats[slave_config.slave_id] = ConnectionStats()
        self.logger.info(f"Added slave {slave_config.slave_id}: {slave_config.name}")
    
    def remove_slave(self, slave_id: int):
        """Remove a slave device from the server"""
        if slave_id in self.slaves:
            del self.slaves[slave_id]
            del self.stats[slave_id]
            self.logger.info(f"Removed slave {slave_id}")
    
    def start_server(self):
        """Start the Modbus server"""
        if self.is_running:
            self.logger.warning("Server is already running")
            return
        
        try:
            # Open serial connection
            self._connect_serial()
            
            # Start server thread
            self.is_running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            # Start performance monitoring
            self.performance_monitor.start()
            
            # Start statistics reporting
            self._start_stats_reporting()
            
            self.logger.info("Modbus Industrial Server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            self.is_running = False
            raise
    
    def stop_server(self):
        """Stop the Modbus server"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping Modbus server...")
        self.is_running = False
        
        # Stop performance monitoring
        self.performance_monitor.stop()
        
        # Close serial connection
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        # Wait for server thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
        
        self.logger.info("Modbus server stopped")
    
    def _connect_serial(self):
        """Connect to serial port with retry logic"""
        serial_config = self.config['serial']
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
                
                self.serial_port = serial.Serial(
                    port=serial_config['port'],
                    baudrate=serial_config['baudrate'],
                    bytesize=serial_config['bytesize'],
                    parity=parity_map[serial_config['parity']],
                    stopbits=serial_config['stopbits'],
                    timeout=serial_config['timeout']
                )
                
                self.logger.info(f"Connected to {serial_config['port']} at {serial_config['baudrate']} baud")
                return
                
            except Exception as e:
                self.logger.error(f"Serial connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
    
    def _server_loop(self):
        """Main server loop"""
        self.logger.info("Server loop started")
        
        while self.is_running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    self.logger.warning("Serial connection lost, attempting reconnection...")
                    self._connect_serial()
                    continue
                
                # Check for incoming requests
                if self.serial_port.in_waiting > 0:
                    request_data = self._read_request()
                    if request_data:
                        # Process request in thread pool
                        future = self.executor.submit(self._process_request, request_data)
                        # Don't wait for completion to maintain responsiveness
                
                # Small delay to prevent CPU spinning
                time.sleep(0.001)  # 1ms
                
            except Exception as e:
                self.logger.error(f"Error in server loop: {e}")
                time.sleep(1)  # Longer delay on error
    
    def _read_request(self) -> Optional[bytes]:
        """Read a complete Modbus request from serial port"""
        try:
            # Read minimum frame (slave_id + function_code)
            header = self.serial_port.read(2)
            if len(header) < 2:
                return None
            
            slave_id, function_code = header
            
            # Determine expected frame length based on function code
            if function_code in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]:
                # Standard functions - read remaining 6 bytes (4 data + 2 CRC)
                remaining = self.serial_port.read(6)
                if len(remaining) < 6:
                    return None
                return header + remaining
            
            elif function_code == 0x0F or function_code == 0x10:
                # Write multiple - need to read byte count first
                byte_count_data = self.serial_port.read(4)  # address(2) + quantity(2)
                if len(byte_count_data) < 4:
                    return None
                
                if function_code == 0x0F:
                    # Write multiple coils
                    byte_count = self.serial_port.read(1)[0]
                    data = self.serial_port.read(byte_count + 2)  # data + CRC
                else:
                    # Write multiple registers
                    byte_count = self.serial_port.read(1)[0]
                    data = self.serial_port.read(byte_count + 2)  # data + CRC
                
                return header + byte_count_data + bytes([byte_count]) + data
            
            elif function_code == 0x14:
                # Read file records
                byte_count = self.serial_port.read(1)[0]
                remaining = self.serial_port.read(byte_count + 2)  # data + CRC
                return header + bytes([byte_count]) + remaining
            
            else:
                self.logger.warning(f"Unsupported function code: 0x{function_code:02X}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error reading request: {e}")
            return None
    
    def _process_request(self, request_data: bytes):
        """Process a Modbus request"""
        try:
            if len(request_data) < 4:
                return
            
            slave_id = request_data[0]
            function_code = request_data[1]
            
            # Update statistics
            if slave_id in self.stats:
                self.stats[slave_id].total_requests += 1
                self.stats[slave_id].last_request_time = time.time()
                self.stats[slave_id].bytes_received += len(request_data)
            
            # Check if slave exists
            if slave_id not in self.slaves:
                self._send_exception_response(slave_id, function_code, 0x0B)  # Gateway Target Device Failed
                return
            
            # Validate CRC
            if not self._validate_crc(request_data):
                self.logger.warning(f"CRC validation failed for slave {slave_id}")
                return
            
            # Process based on function code
            response = None
            if function_code == 0x03:  # Read Holding Registers
                response = self._handle_read_holding_registers(slave_id, request_data)
            elif function_code == 0x04:  # Read Input Registers
                response = self._handle_read_input_registers(slave_id, request_data)
            elif function_code == 0x01:  # Read Coils
                response = self._handle_read_coils(slave_id, request_data)
            elif function_code == 0x02:  # Read Discrete Inputs
                response = self._handle_read_discrete_inputs(slave_id, request_data)
            elif function_code == 0x05:  # Write Single Coil
                response = self._handle_write_single_coil(slave_id, request_data)
            elif function_code == 0x06:  # Write Single Register
                response = self._handle_write_single_register(slave_id, request_data)
            elif function_code == 0x0F:  # Write Multiple Coils
                response = self._handle_write_multiple_coils(slave_id, request_data)
            elif function_code == 0x10:  # Write Multiple Registers
                response = self._handle_write_multiple_registers(slave_id, request_data)
            elif function_code == 0x14:  # Read File Records
                response = self._handle_read_file_records(slave_id, request_data)
            else:
                self._send_exception_response(slave_id, function_code, 0x01)  # Illegal Function
                return
            
            if response:
                self._send_response(response)
                if slave_id in self.stats:
                    self.stats[slave_id].successful_requests += 1
                    self.stats[slave_id].bytes_sent += len(response)
            else:
                if slave_id in self.stats:
                    self.stats[slave_id].failed_requests += 1
                    
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            if len(request_data) >= 2:
                self._send_exception_response(request_data[0], request_data[1], 0x04)  # Server Device Failure
    
    def _handle_read_holding_registers(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle read holding registers request (function code 0x03)"""
        if len(request_data) < 8:
            return None
        
        start_address = (request_data[2] << 8) | request_data[3]
        quantity = (request_data[4] << 8) | request_data[5]
        
        if quantity < 1 or quantity > 125:
            self._send_exception_response(slave_id, 0x03, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        response_data = [slave_id, 0x03, quantity * 2]  # byte count
        
        try:
            for addr in range(start_address, start_address + quantity):
                if addr in slave.holding_registers:
                    value = slave.holding_registers[addr]
                    response_data.extend([(value >> 8) & 0xFF, value & 0xFF])
                else:
                    # Return 0 for non-existent registers
                    response_data.extend([0x00, 0x00])
            
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error reading holding registers: {e}")
            self._send_exception_response(slave_id, 0x03, 0x04)  # Server Device Failure
            return None
    
    def _handle_read_input_registers(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle read input registers request (function code 0x04)"""
        if len(request_data) < 8:
            return None
        
        start_address = (request_data[2] << 8) | request_data[3]
        quantity = (request_data[4] << 8) | request_data[5]
        
        if quantity < 1 or quantity > 125:
            self._send_exception_response(slave_id, 0x04, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        response_data = [slave_id, 0x04, quantity * 2]  # byte count
        
        try:
            for addr in range(start_address, start_address + quantity):
                if addr in slave.input_registers:
                    value = slave.input_registers[addr]
                    response_data.extend([(value >> 8) & 0xFF, value & 0xFF])
                else:
                    response_data.extend([0x00, 0x00])
            
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error reading input registers: {e}")
            self._send_exception_response(slave_id, 0x04, 0x04)  # Server Device Failure
            return None
    
    def _handle_read_coils(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle read coils request (function code 0x01)"""
        if len(request_data) < 8:
            return None
        
        start_address = (request_data[2] << 8) | request_data[3]
        quantity = (request_data[4] << 8) | request_data[5]
        
        if quantity < 1 or quantity > 2000:
            self._send_exception_response(slave_id, 0x01, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        byte_count = (quantity + 7) // 8  # Round up to nearest byte
        response_data = [slave_id, 0x01, byte_count]
        
        try:
            coil_bytes = []
            for byte_idx in range(byte_count):
                byte_value = 0
                for bit_idx in range(8):
                    coil_addr = start_address + byte_idx * 8 + bit_idx
                    if coil_addr < start_address + quantity:
                        if coil_addr in slave.coils and slave.coils[coil_addr]:
                            byte_value |= (1 << bit_idx)
                coil_bytes.append(byte_value)
            
            response_data.extend(coil_bytes)
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error reading coils: {e}")
            self._send_exception_response(slave_id, 0x01, 0x04)  # Server Device Failure
            return None
    
    def _handle_read_discrete_inputs(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle read discrete inputs request (function code 0x02)"""
        if len(request_data) < 8:
            return None
        
        start_address = (request_data[2] << 8) | request_data[3]
        quantity = (request_data[4] << 8) | request_data[5]
        
        if quantity < 1 or quantity > 2000:
            self._send_exception_response(slave_id, 0x02, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        byte_count = (quantity + 7) // 8  # Round up to nearest byte
        response_data = [slave_id, 0x02, byte_count]
        
        try:
            input_bytes = []
            for byte_idx in range(byte_count):
                byte_value = 0
                for bit_idx in range(8):
                    input_addr = start_address + byte_idx * 8 + bit_idx
                    if input_addr < start_address + quantity:
                        if input_addr in slave.discrete_inputs and slave.discrete_inputs[input_addr]:
                            byte_value |= (1 << bit_idx)
                input_bytes.append(byte_value)
            
            response_data.extend(input_bytes)
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error reading discrete inputs: {e}")
            self._send_exception_response(slave_id, 0x02, 0x04)  # Server Device Failure
            return None
    
    def _handle_write_single_coil(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle write single coil request (function code 0x05)"""
        if len(request_data) < 8:
            return None
        
        coil_address = (request_data[2] << 8) | request_data[3]
        coil_value = (request_data[4] << 8) | request_data[5]
        
        if coil_value not in [0x0000, 0xFF00]:
            self._send_exception_response(slave_id, 0x05, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        
        try:
            slave.coils[coil_address] = (coil_value == 0xFF00)
            
            # Echo back the request as response
            response_bytes = request_data[:-2]  # Remove CRC
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error writing single coil: {e}")
            self._send_exception_response(slave_id, 0x05, 0x04)  # Server Device Failure
            return None
    
    def _handle_write_single_register(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle write single register request (function code 0x06)"""
        if len(request_data) < 8:
            return None
        
        register_address = (request_data[2] << 8) | request_data[3]
        register_value = (request_data[4] << 8) | request_data[5]
        
        slave = self.slaves[slave_id]
        
        try:
            slave.holding_registers[register_address] = register_value
            
            # Echo back the request as response
            response_bytes = request_data[:-2]  # Remove CRC
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error writing single register: {e}")
            self._send_exception_response(slave_id, 0x06, 0x04)  # Server Device Failure
            return None
    
    def _handle_write_multiple_coils(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle write multiple coils request (function code 0x0F)"""
        if len(request_data) < 9:
            return None
        
        start_address = (request_data[2] << 8) | request_data[3]
        quantity = (request_data[4] << 8) | request_data[5]
        byte_count = request_data[6]
        
        if quantity < 1 or quantity > 1968 or byte_count != (quantity + 7) // 8:
            self._send_exception_response(slave_id, 0x0F, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        
        try:
            coil_data = request_data[7:7+byte_count]
            
            for i in range(quantity):
                byte_idx = i // 8
                bit_idx = i % 8
                coil_address = start_address + i
                coil_value = bool(coil_data[byte_idx] & (1 << bit_idx))
                slave.coils[coil_address] = coil_value
            
            # Response: slave_id + function_code + start_address + quantity + CRC
            response_data = [slave_id, 0x0F] + list(request_data[2:6])
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error writing multiple coils: {e}")
            self._send_exception_response(slave_id, 0x0F, 0x04)  # Server Device Failure
            return None
    
    def _handle_write_multiple_registers(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle write multiple registers request (function code 0x10)"""
        if len(request_data) < 9:
            return None
        
        start_address = (request_data[2] << 8) | request_data[3]
        quantity = (request_data[4] << 8) | request_data[5]
        byte_count = request_data[6]
        
        if quantity < 1 or quantity > 123 or byte_count != quantity * 2:
            self._send_exception_response(slave_id, 0x10, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        
        try:
            register_data = request_data[7:7+byte_count]
            
            for i in range(quantity):
                register_address = start_address + i
                register_value = (register_data[i*2] << 8) | register_data[i*2 + 1]
                slave.holding_registers[register_address] = register_value
            
            # Response: slave_id + function_code + start_address + quantity + CRC
            response_data = [slave_id, 0x10] + list(request_data[2:6])
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            return response_bytes + crc
            
        except Exception as e:
            self.logger.error(f"Error writing multiple registers: {e}")
            self._send_exception_response(slave_id, 0x10, 0x04)  # Server Device Failure
            return None
    
    def _handle_read_file_records(self, slave_id: int, request_data: bytes) -> Optional[bytes]:
        """Handle read file records request (function code 0x14)"""
        if len(request_data) < 10:
            return None
        
        byte_count = request_data[2]
        if byte_count != 7:  # Standard file record request
            self._send_exception_response(slave_id, 0x14, 0x03)  # Illegal Data Value
            return None
        
        reference_type = request_data[3]
        file_number = (request_data[4] << 8) | request_data[5]
        record_number = (request_data[6] << 8) | request_data[7]
        record_length = (request_data[8] << 8) | request_data[9]
        
        if reference_type != 6:  # Only support reference type 6
            self._send_exception_response(slave_id, 0x14, 0x03)  # Illegal Data Value
            return None
        
        slave = self.slaves[slave_id]
        
        try:
            if file_number in slave.file_records and record_number in slave.file_records[file_number]:
                file_data = slave.file_records[file_number][record_number]
                # Truncate or pad data to requested length
                if len(file_data) > record_length * 2:
                    file_data = file_data[:record_length * 2]
                elif len(file_data) < record_length * 2:
                    file_data = file_data + b'\x00' * (record_length * 2 - len(file_data))
                
                # Response format: slave_id + function_code + response_data_length + file_response_length + reference_type + data + CRC
                file_response_length = len(file_data) + 1  # +1 for reference type
                response_data_length = file_response_length + 1  # +1 for file_response_length byte
                
                response_data = [slave_id, 0x14, response_data_length, file_response_length, reference_type]
                response_data.extend(file_data)
                
                response_bytes = bytes(response_data)
                crc = self._calculate_crc(response_bytes)
                return response_bytes + crc
            else:
                # File or record not found, return empty data
                file_response_length = 1  # Only reference type
                response_data_length = 2  # file_response_length + reference_type
                
                response_data = [slave_id, 0x14, response_data_length, file_response_length, reference_type]
                response_bytes = bytes(response_data)
                crc = self._calculate_crc(response_bytes)
                return response_bytes + crc
                
        except Exception as e:
            self.logger.error(f"Error reading file records: {e}")
            self._send_exception_response(slave_id, 0x14, 0x04)  # Server Device Failure
            return None
    
    def _calculate_crc(self, data: bytes) -> bytes:
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
    
    def _validate_crc(self, data: bytes) -> bool:
        """Validate CRC-16 of received data"""
        if len(data) < 3:
            return False
        
        received_crc = data[-2:]
        calculated_crc = self._calculate_crc(data[:-2])
        return received_crc == calculated_crc
    
    def _send_response(self, response: bytes):
        """Send response to serial port"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(response)
                self.serial_port.flush()
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
    
    def _send_exception_response(self, slave_id: int, function_code: int, exception_code: int):
        """Send Modbus exception response"""
        try:
            response_data = [slave_id, function_code | 0x80, exception_code]
            response_bytes = bytes(response_data)
            crc = self._calculate_crc(response_bytes)
            full_response = response_bytes + crc
            
            self._send_response(full_response)
            self.logger.warning(f"Sent exception response: Slave {slave_id}, Function 0x{function_code:02X}, Exception 0x{exception_code:02X}")
            
        except Exception as e:
            self.logger.error(f"Error sending exception response: {e}")
    
    def _start_stats_reporting(self):
        """Start statistics reporting thread"""
        def stats_worker():
            while self.is_running:
                try:
                    time.sleep(self.config['server']['stats_interval'])
                    if self.is_running:
                        self._log_statistics()
                except Exception as e:
                    self.logger.error(f"Error in stats reporting: {e}")
        
        stats_thread = threading.Thread(target=stats_worker, daemon=True)
        stats_thread.start()
    
    def _log_statistics(self):
        """Log server statistics"""
        try:
            total_requests = sum(stats.total_requests for stats in self.stats.values())
            total_successful = sum(stats.successful_requests for stats in self.stats.values())
            total_failed = sum(stats.failed_requests for stats in self.stats.values())
            
            success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
            
            self.logger.info(f"Server Statistics - Total Requests: {total_requests}, "
                           f"Success Rate: {success_rate:.1f}%, Failed: {total_failed}")
            
            for slave_id, stats in self.stats.items():
                if stats.total_requests > 0:
                    slave_success_rate = (stats.successful_requests / stats.total_requests * 100)
                    self.logger.info(f"Slave {slave_id}: {stats.total_requests} requests, "
                                   f"{slave_success_rate:.1f}% success, "
                                   f"{stats.bytes_sent} bytes sent, {stats.bytes_received} bytes received")
                    
        except Exception as e:
            self.logger.error(f"Error logging statistics: {e}")
    
    def get_slave_data(self, slave_id: int) -> Optional[Dict[str, Any]]:
        """Get slave data for external access"""
        if slave_id not in self.slaves:
            return None
        
        slave = self.slaves[slave_id]
        stats = self.stats[slave_id]
        
        return {
            'slave_id': slave.slave_id,
            'name': slave.name,
            'description': slave.description,
            'holding_registers': dict(slave.holding_registers),
            'input_registers': dict(slave.input_registers),
            'coils': dict(slave.coils),
            'discrete_inputs': dict(slave.discrete_inputs),
            'statistics': asdict(stats)
        }
    
    def update_register(self, slave_id: int, register_type: str, address: int, value: Any) -> bool:
        """Update register value"""
        if slave_id not in self.slaves:
            return False
        
        slave = self.slaves[slave_id]
        
        try:
            if register_type == 'holding':
                slave.holding_registers[address] = int(value)
            elif register_type == 'input':
                slave.input_registers[address] = int(value)
            elif register_type == 'coil':
                slave.coils[address] = bool(value)
            elif register_type == 'discrete':
                slave.discrete_inputs[address] = bool(value)
            else:
                return False
            
            self.logger.debug(f"Updated {register_type} register {address} = {value} for slave {slave_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating register: {e}")
            return False


class PerformanceMonitor:
    """Performance monitoring for Pi Zero 2W optimization"""
    
    def __init__(self):
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger('PerformanceMonitor')
    
    def start(self):
        """Start performance monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Performance monitoring loop"""
        while self.is_monitoring:
            try:
                # Check memory usage
                memory_info = psutil.virtual_memory()
                memory_usage_mb = memory_info.used / 1024 / 1024
                memory_percent = memory_info.percent
                
                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Log warnings if thresholds exceeded
                if memory_usage_mb > PI_ZERO_CONFIG['memory_limit_mb']:
                    self.logger.warning(f"Memory usage high: {memory_usage_mb:.1f}MB ({memory_percent:.1f}%)")
                
                if cpu_percent > PI_ZERO_CONFIG['cpu_threshold']:
                    self.logger.warning(f"CPU usage high: {cpu_percent:.1f}%")
                
                # Log periodic status
                self.logger.debug(f"Performance: CPU {cpu_percent:.1f}%, Memory {memory_usage_mb:.1f}MB")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in performance monitoring: {e}")
                time.sleep(10)


def create_example_slave() -> SlaveConfig:
    """Create an example slave configuration"""
    return SlaveConfig(
        slave_id=1,
        name="Example Industrial Device",
        description="Simulated industrial device for testing",
        holding_registers={
            2014: 16256,  # Example float value (part 1)
            2015: 17095,  # Example float value (part 2)
            2016: 1000,   # Temperature sensor
            2017: 2500,   # Pressure sensor
            2018: 750,    # Flow rate
        },
        input_registers={
            3001: 25,     # Temperature reading
            3002: 1013,   # Atmospheric pressure
            3003: 60,     # Humidity
        },
        coils={
            1: True,      # Motor 1 status
            2: False,     # Motor 2 status
            3: True,      # Pump status
        },
        discrete_inputs={
            10001: True,  # Emergency stop
            10002: False, # Door open
            10003: True,  # System ready
        },
        file_records={
            1: {
                0: b"INDUSTRIAL_DEVICE_V1.0\x00\x00\x00\x00\x00\x00\x00\x00",
                1: b"SERIAL_12345678\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                2: b"CONFIG_DATA_HERE\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            }
        }
    )


def main():
    """Main function for running the server"""
    print("Modbus Industrial Server for Raspberry Pi Zero 2W")
    print("=" * 50)
    
    try:
        # Create server instance
        server = ModbusIndustrialServer()
        
        # Add example slave
        example_slave = create_example_slave()
        server.add_slave(example_slave)
        
        print(f"Added example slave: {example_slave.name}")
        print(f"Slave ID: {example_slave.slave_id}")
        print(f"Holding registers: {len(example_slave.holding_registers)}")
        print(f"Input registers: {len(example_slave.input_registers)}")
        print(f"Coils: {len(example_slave.coils)}")
        print(f"Discrete inputs: {len(example_slave.discrete_inputs)}")
        print()
        
        # Start server
        print("Starting Modbus server...")
        server.start_server()
        
        print("Server started successfully!")
        print("Press Ctrl+C to stop the server")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server.stop_server()
            print("Server stopped.")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
