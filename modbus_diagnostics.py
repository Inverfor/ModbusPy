#!/usr/bin/env python3
"""
Modbus Server Diagnostics and Monitoring Tool
Real-time monitoring, diagnostics, and management interface for the Modbus Industrial Server
Optimized for Raspberry Pi Zero 2W
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import json
import psutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from modbus_industrial_server import ModbusIndustrialServer, create_example_slave

class ModbusDiagnostics:
    """Diagnostics and monitoring GUI for Modbus Industrial Server"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus Industrial Server - Diagnostics & Monitoring")
        self.root.geometry("1200x800")
        
        # Server instance
        self.server: Optional[ModbusIndustrialServer] = None
        self.server_running = False
        
        # Monitoring data
        self.cpu_data = []
        self.memory_data = []
        self.request_data = []
        self.timestamps = []
        self.max_data_points = 100
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        self.create_widgets()
        self.start_monitoring()
    
    def create_widgets(self):
        """Create the GUI widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Server Control Tab
        self.create_server_control_tab()
        
        # System Monitor Tab
        self.create_system_monitor_tab()
        
        # Slave Management Tab
        self.create_slave_management_tab()
        
        # Statistics Tab
        self.create_statistics_tab()
        
        # Logs Tab
        self.create_logs_tab()
        
        # Configuration Tab
        self.create_configuration_tab()
    
    def create_server_control_tab(self):
        """Create server control tab"""
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Server Control")
        
        # Server Status Frame
        status_frame = ttk.LabelFrame(control_frame, text="Server Status", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status indicators
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.status_var = tk.StringVar(value="Stopped")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(status_frame, text="Uptime:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.uptime_var = tk.StringVar(value="00:00:00")
        ttk.Label(status_frame, textvariable=self.uptime_var).grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(status_frame, text="Active Slaves:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.slaves_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.slaves_var).grid(row=0, column=5, sticky=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.grid(row=1, column=0, columnspan=6, pady=(10, 0))
        
        self.start_btn = ttk.Button(button_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.restart_btn = ttk.Button(button_frame, text="Restart Server", command=self.restart_server, state=tk.DISABLED)
        self.restart_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Add Example Slave", command=self.add_example_slave).pack(side=tk.LEFT, padx=(0, 5))
        
        # Serial Configuration Frame
        serial_frame = ttk.LabelFrame(control_frame, text="Serial Configuration", padding="10")
        serial_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Port
        ttk.Label(serial_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.port_var = tk.StringVar(value="/dev/ttyUSB0")
        port_entry = ttk.Entry(serial_frame, textvariable=self.port_var, width=15)
        port_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Baudrate
        ttk.Label(serial_frame, text="Baudrate:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_combo = ttk.Combobox(serial_frame, textvariable=self.baudrate_var, 
                                     values=["9600", "19200", "38400", "57600", "115200"], width=12)
        baudrate_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Parity
        ttk.Label(serial_frame, text="Parity:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.parity_var = tk.StringVar(value="N")
        parity_combo = ttk.Combobox(serial_frame, textvariable=self.parity_var, 
                                   values=["N", "E", "O"], width=8)
        parity_combo.grid(row=0, column=5, sticky=tk.W)
        
        # Apply button
        ttk.Button(serial_frame, text="Apply Configuration", 
                  command=self.apply_serial_config).grid(row=1, column=0, columnspan=6, pady=(10, 0))
    
    def create_system_monitor_tab(self):
        """Create system monitoring tab"""
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="System Monitor")
        
        # System Info Frame
        info_frame = ttk.LabelFrame(monitor_frame, text="System Information", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # CPU Info
        ttk.Label(info_frame, text="CPU:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.cpu_info_var = tk.StringVar(value="Loading...")
        ttk.Label(info_frame, textvariable=self.cpu_info_var).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Memory Info
        ttk.Label(info_frame, text="Memory:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.memory_info_var = tk.StringVar(value="Loading...")
        ttk.Label(info_frame, textvariable=self.memory_info_var).grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Temperature
        ttk.Label(info_frame, text="Temperature:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.temp_var = tk.StringVar(value="Loading...")
        ttk.Label(info_frame, textvariable=self.temp_var).grid(row=1, column=1, sticky=tk.W, padx=(0, 20))
        
        # Disk Usage
        ttk.Label(info_frame, text="Disk Usage:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        self.disk_var = tk.StringVar(value="Loading...")
        ttk.Label(info_frame, textvariable=self.disk_var).grid(row=1, column=3, sticky=tk.W)
        
        # Performance Charts Frame
        charts_frame = ttk.LabelFrame(monitor_frame, text="Performance Charts", padding="10")
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.fig.suptitle('System Performance Monitoring')
        
        # CPU subplot
        self.cpu_ax = self.fig.add_subplot(221)
        self.cpu_ax.set_title('CPU Usage (%)')
        self.cpu_ax.set_ylim(0, 100)
        
        # Memory subplot
        self.memory_ax = self.fig.add_subplot(222)
        self.memory_ax.set_title('Memory Usage (MB)')
        
        # Request rate subplot
        self.request_ax = self.fig.add_subplot(223)
        self.request_ax.set_title('Request Rate (req/min)')
        
        # Temperature subplot
        self.temp_ax = self.fig.add_subplot(224)
        self.temp_ax.set_title('Temperature (°C)')
        self.temp_ax.set_ylim(0, 85)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, charts_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def create_slave_management_tab(self):
        """Create slave management tab"""
        slave_frame = ttk.Frame(self.notebook)
        self.notebook.add(slave_frame, text="Slave Management")
        
        # Slave List Frame
        list_frame = ttk.LabelFrame(slave_frame, text="Active Slaves", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for slaves
        columns = ('ID', 'Name', 'Description', 'Registers', 'Last Request', 'Status')
        self.slave_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.slave_tree.heading(col, text=col)
            self.slave_tree.column(col, width=120)
        
        # Scrollbar for treeview
        slave_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.slave_tree.yview)
        self.slave_tree.configure(yscrollcommand=slave_scrollbar.set)
        
        self.slave_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        slave_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Slave control buttons
        slave_control_frame = ttk.Frame(slave_frame)
        slave_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(slave_control_frame, text="Refresh", command=self.refresh_slaves).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(slave_control_frame, text="View Details", command=self.view_slave_details).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(slave_control_frame, text="Remove Slave", command=self.remove_slave).pack(side=tk.LEFT, padx=(0, 5))
    
    def create_statistics_tab(self):
        """Create statistics tab"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="Statistics")
        
        # Overall Statistics Frame
        overall_frame = ttk.LabelFrame(stats_frame, text="Overall Statistics", padding="10")
        overall_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Statistics labels
        stats_labels = [
            ("Total Requests:", "total_requests_var"),
            ("Successful Requests:", "successful_requests_var"),
            ("Failed Requests:", "failed_requests_var"),
            ("Success Rate:", "success_rate_var"),
            ("Bytes Sent:", "bytes_sent_var"),
            ("Bytes Received:", "bytes_received_var")
        ]
        
        for i, (label, var_name) in enumerate(stats_labels):
            row = i // 3
            col = (i % 3) * 2
            
            ttk.Label(overall_frame, text=label).grid(row=row, column=col, sticky=tk.W, padx=(0, 5))
            var = tk.StringVar(value="0")
            setattr(self, var_name, var)
            ttk.Label(overall_frame, textvariable=var).grid(row=row, column=col+1, sticky=tk.W, padx=(0, 20))
        
        # Per-Slave Statistics Frame
        slave_stats_frame = ttk.LabelFrame(stats_frame, text="Per-Slave Statistics", padding="10")
        slave_stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Statistics treeview
        stats_columns = ('Slave ID', 'Name', 'Requests', 'Success Rate', 'Bytes Sent', 'Bytes Received', 'Last Request')
        self.stats_tree = ttk.Treeview(slave_stats_frame, columns=stats_columns, show='headings', height=15)
        
        for col in stats_columns:
            self.stats_tree.heading(col, text=col)
            self.stats_tree.column(col, width=100)
        
        # Scrollbar for stats treeview
        stats_scrollbar = ttk.Scrollbar(slave_stats_frame, orient=tk.VERTICAL, command=self.stats_tree.yview)
        self.stats_tree.configure(yscrollcommand=stats_scrollbar.set)
        
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Refresh button
        ttk.Button(slave_stats_frame, text="Refresh Statistics", 
                  command=self.refresh_statistics).pack(pady=(10, 0))
    
    def create_logs_tab(self):
        """Create logs tab"""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")
        
        # Log controls
        log_control_frame = ttk.Frame(logs_frame)
        log_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(log_control_frame, text="Log Level:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(log_control_frame, textvariable=self.log_level_var,
                                      values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], width=10)
        log_level_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(log_control_frame, text="Refresh Logs", command=self.refresh_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_control_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_control_frame, text="Export Logs", command=self.export_logs).pack(side=tk.LEFT)
        
        # Log display
        log_display_frame = ttk.LabelFrame(logs_frame, text="Log Messages", padding="10")
        log_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_display_frame, height=25, width=120)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def create_configuration_tab(self):
        """Create configuration tab"""
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
        
        # Configuration editor
        config_editor_frame = ttk.LabelFrame(config_frame, text="Server Configuration", padding="10")
        config_editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.config_text = scrolledtext.ScrolledText(config_editor_frame, height=25, width=120)
        self.config_text.pack(fill=tk.BOTH, expand=True)
        
        # Configuration controls
        config_control_frame = ttk.Frame(config_frame)
        config_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(config_control_frame, text="Load Configuration", 
                  command=self.load_configuration).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_control_frame, text="Save Configuration", 
                  command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_control_frame, text="Reset to Defaults", 
                  command=self.reset_configuration).pack(side=tk.LEFT)
        
        # Load initial configuration
        self.load_configuration()
    
    def start_server(self):
        """Start the Modbus server"""
        try:
            if self.server is None:
                self.server = ModbusIndustrialServer()
            
            # Apply serial configuration
            self.apply_serial_config()
            
            self.server.start_server()
            self.server_running = True
            
            # Update UI
            self.status_var.set("Running")
            self.status_label.config(foreground="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.restart_btn.config(state=tk.NORMAL)
            
            self.log_message("Server started successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            self.log_message(f"Failed to start server: {str(e)}")
    
    def stop_server(self):
        """Stop the Modbus server"""
        try:
            if self.server:
                self.server.stop_server()
            
            self.server_running = False
            
            # Update UI
            self.status_var.set("Stopped")
            self.status_label.config(foreground="red")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.restart_btn.config(state=tk.DISABLED)
            
            self.log_message("Server stopped")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop server: {str(e)}")
            self.log_message(f"Failed to stop server: {str(e)}")
    
    def restart_server(self):
        """Restart the Modbus server"""
        self.stop_server()
        time.sleep(1)
        self.start_server()
    
    def add_example_slave(self):
        """Add an example slave to the server"""
        try:
            if not self.server:
                self.server = ModbusIndustrialServer()
            
            example_slave = create_example_slave()
            self.server.add_slave(example_slave)
            
            self.refresh_slaves()
            self.log_message(f"Added example slave: {example_slave.name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add example slave: {str(e)}")
            self.log_message(f"Failed to add example slave: {str(e)}")
    
    def apply_serial_config(self):
        """Apply serial configuration to server"""
        if self.server:
            self.server.config['serial']['port'] = self.port_var.get()
            self.server.config['serial']['baudrate'] = int(self.baudrate_var.get())
            self.server.config['serial']['parity'] = self.parity_var.get()
            self.log_message("Serial configuration applied")
    
    def start_monitoring(self):
        """Start system monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)
    
    def monitoring_loop(self):
        """Main monitoring loop"""
        start_time = time.time()
        
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Update uptime
                if self.server_running:
                    uptime_seconds = int(current_time - start_time)
                    hours = uptime_seconds // 3600
                    minutes = (uptime_seconds % 3600) // 60
                    seconds = uptime_seconds % 60
                    self.uptime_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Update system information
                self.update_system_info()
                
                # Update performance charts
                self.update_performance_charts()
                
                # Update slave count
                if self.server:
                    self.slaves_var.set(str(len(self.server.slaves)))
                
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                self.log_message(f"Monitoring error: {str(e)}")
                time.sleep(5)
    
    def update_system_info(self):
        """Update system information"""
        try:
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            self.cpu_info_var.set(f"{cpu_percent:.1f}% ({cpu_count} cores)")
            
            # Memory info
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            self.memory_info_var.set(f"{memory_mb:.1f}MB ({memory.percent:.1f}%)")
            
            # Temperature (Pi-specific)
            try:
                temp_result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                           capture_output=True, text=True, timeout=2)
                if temp_result.returncode == 0:
                    temp_str = temp_result.stdout.strip()
                    temp = float(temp_str.split('=')[1].split("'")[0])
                    self.temp_var.set(f"{temp:.1f}°C")
                else:
                    self.temp_var.set("N/A")
            except:
                self.temp_var.set("N/A")
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_var.set(f"{disk_percent:.1f}%")
            
        except Exception as e:
            self.log_message(f"System info update error: {str(e)}")
    
    def update_performance_charts(self):
        """Update performance charts"""
        try:
            current_time = datetime.now()
            
            # Get current data
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_mb = psutil.virtual_memory().used / 1024 / 1024
            
            # Get temperature
            temp = 0
            try:
                temp_result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                           capture_output=True, text=True, timeout=1)
                if temp_result.returncode == 0:
                    temp_str = temp_result.stdout.strip()
                    temp = float(temp_str.split('=')[1].split("'")[0])
            except:
                pass
            
            # Get request rate (if server is running)
            request_rate = 0
            if self.server and self.server_running:
                total_requests = sum(stats.total_requests for stats in self.server.stats.values())
                if len(self.request_data) > 0:
                    request_rate = max(0, total_requests - self.request_data[-1]) * 30  # requests per minute
                else:
                    request_rate = 0
            
            # Add data points
            self.timestamps.append(current_time)
            self.cpu_data.append(cpu_percent)
            self.memory_data.append(memory_mb)
            self.request_data.append(total_requests if self.server else 0)
            
            # Limit data points
            if len(self.timestamps) > self.max_data_points:
                self.timestamps.pop(0)
                self.cpu_data.pop(0)
                self.memory_data.pop(0)
                self.request_data.pop(0)
            
            # Update charts
            if len(self.timestamps) > 1:
                # Clear axes
                self.cpu_ax.clear()
                self.memory_ax.clear()
                self.request_ax.clear()
                self.temp_ax.clear()
                
                # Plot data
                self.cpu_ax.plot(self.timestamps, self.cpu_data, 'b-')
                self.cpu_ax.set_title('CPU Usage (%)')
                self.cpu_ax.set_ylim(0, 100)
                
                self.memory_ax.plot(self.timestamps, self.memory_data, 'g-')
                self.memory_ax.set_title('Memory Usage (MB)')
                
                # Calculate request rates
                request_rates = []
                for i in range(1, len(self.request_data)):
                    rate = (self.request_data[i] - self.request_data[i-1]) * 30  # per minute
                    request_rates.append(max(0, rate))
                
                if request_rates:
                    self.request_ax.plot(self.timestamps[1:], request_rates, 'r-')
                self.request_ax.set_title('Request Rate (req/min)')
                
                # Temperature (constant line for now)
                temp_data = [temp] * len(self.timestamps)
                self.temp_ax.plot(self.timestamps, temp_data, 'orange')
                self.temp_ax.set_title('Temperature (°C)')
                self.temp_ax.set_ylim(0, 85)
                
                # Format x-axis
                for ax in [self.cpu_ax, self.memory_ax, self.request_ax, self.temp_ax]:
                    ax.tick_params(axis='x', rotation=45)
                
                self.fig.tight_layout()
                self.canvas.draw()
                
        except Exception as e:
            self.log_message(f"Chart update error: {str(e)}")
    
    def refresh_slaves(self):
        """Refresh slave list"""
        try:
            # Clear existing items
            for item in self.slave_tree.get_children():
                self.slave_tree.delete(item)
            
            if self.server:
                for slave_id, slave in self.server.slaves.items():
                    stats = self.server.stats.get(slave_id)
                    
                    last_request = "Never"
                    if stats and stats.last_request_time > 0:
                        last_request = datetime.fromtimestamp(stats.last_request_time).strftime("%H:%M:%S")
                    
                    total_registers = (len(slave.holding_registers) + len(slave.input_registers) + 
                                     len(slave.coils) + len(slave.discrete_inputs))
                    
                    status = "Active" if stats and stats.total_requests > 0 else "Inactive"
                    
                    self.slave_tree.insert('', 'end', values=(
                        slave_id, slave.name, slave.description, 
                        total_registers, last_request, status
                    ))
                    
        except Exception as e:
            self.log_message(f"Slave refresh error: {str(e)}")
    
    def view_slave_details(self):
        """View detailed information about selected slave"""
        selection = self.slave_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a slave to view details")
            return
        
        item = self.slave_tree.item(selection[0])
        slave_id = int(item['values'][0])
        
        if self.server and slave_id in self.server.slaves:
            slave_data = self.server.get_slave_data(slave_id)
            
            # Create details window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"Slave {slave_id} Details")
            details_window.geometry("600x400")
            
            details_text = scrolledtext.ScrolledText(details_window, height=20, width=70)
            details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Format slave data
            details_text.insert(tk.END, f"Slave ID: {slave_data['slave_id']}\n")
            details_text.insert(tk.END, f"Name: {slave_data['name']}\n")
            details_text.insert(tk.END, f"Description: {slave_data['description']}\n\n")
            
            details_text.insert(tk.END, "Holding Registers:\n")
            for addr, value in slave_data['holding_registers'].items():
                details_text.insert(tk.END, f"  {addr}: {value}\n")
            
            details_text.insert(tk.END, "\nInput Registers:\n")
            for addr, value in slave_data['input_registers'].items():
                details_text.insert(tk.END, f"  {addr}: {value}\n")
            
            details_text.insert(tk.END, "\nCoils:\n")
            for addr, value in slave_data['coils'].items():
                details_text.insert(tk.END, f"  {addr}: {value}\n")
            
            details_text.insert(tk.END, "\nDiscrete Inputs:\n")
            for addr, value in slave_data['discrete_inputs'].items():
                details_text.insert(tk.END, f"  {addr}: {value}\n")
            
            details_text.insert(tk.END, "\nStatistics:\n")
            stats = slave_data['statistics']
            details_text.insert(tk.END, f"  Total Requests: {stats['total_requests']}\n")
            details_text.insert(tk.END, f"  Successful Requests: {stats['successful_requests']}\n")
            details_text.insert(tk.END, f"  Failed Requests: {stats['failed_requests']}\n")
            details_text.insert(tk.END, f"  Bytes Sent: {stats['bytes_sent']}\n")
            details_text.insert(tk.END, f"  Bytes Received: {stats['bytes_received']}\n")
            
            if stats['last_request_time'] > 0:
                last_time = datetime.fromtimestamp(stats['last_request_time'])
                details_text.insert(tk.END, f"  Last Request: {last_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def remove_slave(self):
        """Remove selected slave"""
        selection = self.slave_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a slave to remove")
            return
        
        item = self.slave_tree.item(selection[0])
        slave_id = int(item['values'][0])
        
        if messagebox.askyesno("Confirm", f"Remove slave {slave_id}?"):
            if self.server:
                self.server.remove_slave(slave_id)
                self.refresh_slaves()
                self.log_message(f"Removed slave {slave_id}")
    
    def refresh_statistics(self):
        """Refresh statistics display"""
        try:
            # Clear existing items
            for item in self.stats_tree.get_children():
                self.stats_tree.delete(item)
            
            if self.server:
                # Overall statistics
                total_requests = sum(stats.total_requests for stats in self.server.stats.values())
                total_successful = sum(stats.successful_requests for stats in self.server.stats.values())
                total_failed = sum(stats.failed_requests for stats in self.server.stats.values())
                total_bytes_sent = sum(stats.bytes_sent for stats in self.server.stats.values())
                total_bytes_received = sum(stats.bytes_received for stats in self.server.stats.values())
                
                success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
                
                self.total_requests_var.set(str(total_requests))
                self.successful_requests_var.set(str(total_successful))
                self.failed_requests_var.set(str(total_failed))
                self.success_rate_var.set(f"{success_rate:.1f}%")
                self.bytes_sent_var.set(str(total_bytes_sent))
                self.bytes_received_var.set(str(total_bytes_received))
                
                # Per-slave statistics
                for slave_id, slave in self.server.slaves.items():
                    stats = self.server.stats.get(slave_id)
                    if stats:
                        slave_success_rate = (stats.successful_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0
                        
                        last_request = "Never"
                        if stats.last_request_time > 0:
                            last_request = datetime.fromtimestamp(stats.last_request_time).strftime("%H:%M:%S")
                        
                        self.stats_tree.insert('', 'end', values=(
                            slave_id, slave.name, stats.total_requests,
                            f"{slave_success_rate:.1f}%", stats.bytes_sent,
                            stats.bytes_received, last_request
                        ))
                        
        except Exception as e:
            self.log_message(f"Statistics refresh error: {str(e)}")
    
    def refresh_logs(self):
        """Refresh log display"""
        try:
            # For now, just add a placeholder message
            # In a real implementation, you would read from the log file
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, "Log refresh functionality - would read from log file\n")
            self.log_text.insert(tk.END, f"Current log level: {self.log_level_var.get()}\n")
            self.log_text.insert(tk.END, f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        except Exception as e:
            self.log_message(f"Log refresh error: {str(e)}")
    
    def clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
    
    def export_logs(self):
        """Export logs to file"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Logs exported to {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export logs: {str(e)}")
    
    def load_configuration(self):
        """Load configuration from file"""
        try:
            with open("modbus_server_config.json", 'r') as f:
                config = json.load(f)
            
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, json.dumps(config, indent=4))
            
        except Exception as e:
            self.log_message(f"Configuration load error: {str(e)}")
    
    def save_configuration(self):
        """Save configuration to file"""
        try:
            config_str = self.config_text.get(1.0, tk.END)
            config = json.loads(config_str)
            
            with open("modbus_server_config.json", 'w') as f:
                json.dump(config, f, indent=4)
            
            messagebox.showinfo("Success", "Configuration saved successfully")
            self.log_message("Configuration saved")
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON format: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def reset_configuration(self):
        """Reset configuration to defaults"""
        if messagebox.askyesno("Confirm", "Reset configuration to defaults?"):
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
            
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, json.dumps(default_config, indent=4))
    
    def log_message(self, message: str):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def on_closing(self):
        """Handle window closing"""
        self.stop_monitoring()
        if self.server_running:
            self.stop_server()
        self.root.destroy()


def main():
    """Main function for running the diagnostics tool"""
    root = tk.Tk()
    app = ModbusDiagnostics(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
