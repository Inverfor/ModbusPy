#!/usr/bin/env python3
"""
Modbus Web Server - Interfaz Web Gráfica para Servidor Modbus Industrial
Optimizado para Raspberry Pi Zero 2W con SQLite para almacenamiento de datos
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Any
import logging
from contextlib import contextmanager
from modbus_industrial_server import ModbusIndustrialServer, create_example_slave

# Configuración optimizada para Pi Zero 2W
WEB_SERVER_CONFIG = {
    'host': '0.0.0.0',
    'port': 8080,
    'debug': False,
    'threaded': True,
    'max_connections': 10,
    'data_retention_days': 30,
    'sampling_interval': 5,  # segundos
    'db_path': 'modbus_data.db',
    'static_folder': 'static',
    'template_folder': 'templates'
}

class ModbusWebServer:
    """Servidor Web para monitoreo y control del servidor Modbus Industrial"""
    
    def __init__(self, modbus_server: Optional[ModbusIndustrialServer] = None):
        self.app = Flask(__name__, 
                        static_folder=WEB_SERVER_CONFIG['static_folder'],
                        template_folder=WEB_SERVER_CONFIG['template_folder'])
        
        self.modbus_server = modbus_server
        self.db_path = WEB_SERVER_CONFIG['db_path']
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('ModbusWebServer')
        
        # Inicializar base de datos
        self.init_database()
        
        # Configurar rutas
        self.setup_routes()
        
        # Thread para recolección de datos
        self.data_collection_active = False
        self.data_collection_thread: Optional[threading.Thread] = None
        
        self.logger.info("Modbus Web Server inicializado")
    
    def init_database(self):
        """Inicializar base de datos SQLite"""
        try:
            with self.get_db_connection() as conn:
                # Tabla para datos de esclavos
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS slave_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        slave_id INTEGER NOT NULL,
                        slave_name TEXT,
                        register_type TEXT NOT NULL,
                        register_address INTEGER NOT NULL,
                        register_value REAL NOT NULL,
                        quality TEXT DEFAULT 'GOOD'
                    )
                ''')
                
                # Tabla para estadísticas de esclavos
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS slave_statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        slave_id INTEGER NOT NULL,
                        total_requests INTEGER DEFAULT 0,
                        successful_requests INTEGER DEFAULT 0,
                        failed_requests INTEGER DEFAULT 0,
                        bytes_sent INTEGER DEFAULT 0,
                        bytes_received INTEGER DEFAULT 0,
                        last_request_time DATETIME
                    )
                ''')
                
                # Tabla para eventos del sistema
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        event_type TEXT NOT NULL,
                        event_description TEXT,
                        severity TEXT DEFAULT 'INFO'
                    )
                ''')
                
                # Tabla para configuración de esclavos
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS slave_config (
                        slave_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        config_json TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Índices para optimizar consultas
                conn.execute('CREATE INDEX IF NOT EXISTS idx_slave_data_timestamp ON slave_data(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_slave_data_slave_id ON slave_data(slave_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_slave_statistics_timestamp ON slave_statistics(timestamp)')
                
                conn.commit()
                self.logger.info("Base de datos inicializada correctamente")
                
        except Exception as e:
            self.logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    @contextmanager
    def get_db_connection(self):
        """Context manager para conexiones a la base de datos"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row  # Para acceso por nombre de columna
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error en conexión a base de datos: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def setup_routes(self):
        """Configurar rutas de la aplicación web"""
        
        @self.app.route('/')
        def index():
            """Página principal del dashboard"""
            return render_template('dashboard.html')
        
        @self.app.route('/slaves')
        def slaves_page():
            """Página de gestión de esclavos"""
            return render_template('slaves.html')
        
        @self.app.route('/charts')
        def charts_page():
            """Página de gráficos y tendencias"""
            return render_template('charts.html')
        
        @self.app.route('/config')
        def config_page():
            """Página de configuración"""
            return render_template('config.html')
        
        # API Routes
        @self.app.route('/api/slaves')
        def api_get_slaves():
            """API: Obtener lista de esclavos"""
            try:
                slaves = []
                if self.modbus_server:
                    for slave_id, slave in self.modbus_server.slaves.items():
                        stats = self.modbus_server.stats.get(slave_id)
                        slaves.append({
                            'id': slave_id,
                            'name': slave.name,
                            'description': slave.description,
                            'status': 'active' if stats and stats.total_requests > 0 else 'inactive',
                            'total_registers': (len(slave.holding_registers) + 
                                              len(slave.input_registers) + 
                                              len(slave.coils) + 
                                              len(slave.discrete_inputs)),
                            'last_request': stats.last_request_time if stats else 0
                        })
                
                return jsonify({'success': True, 'slaves': slaves})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/slave/<int:slave_id>')
        def api_get_slave_details(slave_id):
            """API: Obtener detalles de un esclavo específico"""
            try:
                if self.modbus_server and slave_id in self.modbus_server.slaves:
                    slave_data = self.modbus_server.get_slave_data(slave_id)
                    return jsonify({'success': True, 'slave': slave_data})
                else:
                    return jsonify({'success': False, 'error': 'Slave not found'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/slave/<int:slave_id>/data')
        def api_get_slave_data(slave_id):
            """API: Obtener datos históricos de un esclavo"""
            try:
                hours = request.args.get('hours', 24, type=int)
                start_time = datetime.now() - timedelta(hours=hours)
                
                with self.get_db_connection() as conn:
                    cursor = conn.execute('''
                        SELECT timestamp, register_type, register_address, register_value, quality
                        FROM slave_data 
                        WHERE slave_id = ? AND timestamp >= ?
                        ORDER BY timestamp DESC
                        LIMIT 1000
                    ''', (slave_id, start_time))
                    
                    data = []
                    for row in cursor.fetchall():
                        data.append({
                            'timestamp': row['timestamp'],
                            'register_type': row['register_type'],
                            'register_address': row['register_address'],
                            'register_value': row['register_value'],
                            'quality': row['quality']
                        })
                
                return jsonify({'success': True, 'data': data})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/slave/<int:slave_id>/chart')
        def api_get_slave_chart_data(slave_id):
            """API: Obtener datos para gráficos de un esclavo"""
            try:
                hours = request.args.get('hours', 24, type=int)
                register_address = request.args.get('register', type=int)
                start_time = datetime.now() - timedelta(hours=hours)
                
                query = '''
                    SELECT timestamp, register_address, register_value
                    FROM slave_data 
                    WHERE slave_id = ? AND timestamp >= ?
                '''
                params = [slave_id, start_time]
                
                if register_address is not None:
                    query += ' AND register_address = ?'
                    params.append(register_address)
                
                query += ' ORDER BY timestamp ASC'
                
                with self.get_db_connection() as conn:
                    cursor = conn.execute(query, params)
                    
                    chart_data = {}
                    for row in cursor.fetchall():
                        addr = row['register_address']
                        if addr not in chart_data:
                            chart_data[addr] = {'timestamps': [], 'values': []}
                        
                        chart_data[addr]['timestamps'].append(row['timestamp'])
                        chart_data[addr]['values'].append(row['register_value'])
                
                return jsonify({'success': True, 'chart_data': chart_data})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/statistics')
        def api_get_statistics():
            """API: Obtener estadísticas generales"""
            try:
                stats = {
                    'total_slaves': 0,
                    'active_slaves': 0,
                    'total_requests': 0,
                    'success_rate': 0,
                    'data_points': 0
                }
                
                if self.modbus_server:
                    stats['total_slaves'] = len(self.modbus_server.slaves)
                    stats['active_slaves'] = sum(1 for s in self.modbus_server.stats.values() 
                                                if s.total_requests > 0)
                    stats['total_requests'] = sum(s.total_requests for s in self.modbus_server.stats.values())
                    total_successful = sum(s.successful_requests for s in self.modbus_server.stats.values())
                    stats['success_rate'] = (total_successful / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
                
                # Contar puntos de datos en la base de datos
                with self.get_db_connection() as conn:
                    cursor = conn.execute('SELECT COUNT(*) as count FROM slave_data')
                    stats['data_points'] = cursor.fetchone()['count']
                
                return jsonify({'success': True, 'statistics': stats})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/system/status')
        def api_get_system_status():
            """API: Obtener estado del sistema"""
            try:
                import psutil
                
                status = {
                    'server_running': self.modbus_server is not None and self.modbus_server.is_running,
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                    'temperature': self.get_cpu_temperature(),
                    'uptime': self.get_system_uptime()
                }
                
                return jsonify({'success': True, 'status': status})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/slave/<int:slave_id>/update', methods=['POST'])
        def api_update_slave_register(slave_id):
            """API: Actualizar registro de un esclavo"""
            try:
                data = request.get_json()
                register_type = data.get('register_type')
                address = data.get('address')
                value = data.get('value')
                
                if self.modbus_server and self.modbus_server.update_register(slave_id, register_type, address, value):
                    # Registrar el cambio en la base de datos
                    self.log_system_event('register_update', 
                                        f'Updated {register_type} register {address} = {value} for slave {slave_id}')
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Failed to update register'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/server/start', methods=['POST'])
        def api_start_server():
            """API: Iniciar servidor Modbus"""
            try:
                if not self.modbus_server:
                    self.modbus_server = ModbusIndustrialServer()
                    # Agregar esclavo de ejemplo
                    example_slave = create_example_slave()
                    self.modbus_server.add_slave(example_slave)
                
                if not self.modbus_server.is_running:
                    self.modbus_server.start_server()
                    self.start_data_collection()
                    self.log_system_event('server_start', 'Modbus server started via web interface')
                
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/server/stop', methods=['POST'])
        def api_stop_server():
            """API: Detener servidor Modbus"""
            try:
                if self.modbus_server and self.modbus_server.is_running:
                    self.modbus_server.stop_server()
                    self.stop_data_collection()
                    self.log_system_event('server_stop', 'Modbus server stopped via web interface')
                
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
    
    def get_cpu_temperature(self) -> float:
        """Obtener temperatura de la CPU (específico para Raspberry Pi)"""
        try:
            import subprocess
            result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                return float(temp_str.split('=')[1].split("'")[0])
        except:
            pass
        return 0.0
    
    def get_system_uptime(self) -> str:
        """Obtener tiempo de actividad del sistema"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                uptime_hours = int(uptime_seconds // 3600)
                uptime_minutes = int((uptime_seconds % 3600) // 60)
                return f"{uptime_hours}h {uptime_minutes}m"
        except:
            return "Unknown"
    
    def start_data_collection(self):
        """Iniciar recolección de datos en background"""
        if not self.data_collection_active:
            self.data_collection_active = True
            self.data_collection_thread = threading.Thread(target=self.data_collection_loop, daemon=True)
            self.data_collection_thread.start()
            self.logger.info("Data collection started")
    
    def stop_data_collection(self):
        """Detener recolección de datos"""
        self.data_collection_active = False
        if self.data_collection_thread and self.data_collection_thread.is_alive():
            self.data_collection_thread.join(timeout=5)
        self.logger.info("Data collection stopped")
    
    def data_collection_loop(self):
        """Loop principal de recolección de datos"""
        while self.data_collection_active:
            try:
                if self.modbus_server and self.modbus_server.is_running:
                    self.collect_slave_data()
                    self.collect_statistics()
                    self.cleanup_old_data()
                
                time.sleep(WEB_SERVER_CONFIG['sampling_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in data collection: {e}")
                time.sleep(10)  # Esperar más tiempo en caso de error
    
    def collect_slave_data(self):
        """Recolectar datos de todos los esclavos"""
        try:
            with self.get_db_connection() as conn:
                for slave_id, slave in self.modbus_server.slaves.items():
                    # Recolectar holding registers
                    for addr, value in slave.holding_registers.items():
                        conn.execute('''
                            INSERT INTO slave_data 
                            (slave_id, slave_name, register_type, register_address, register_value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (slave_id, slave.name, 'holding', addr, value))
                    
                    # Recolectar input registers
                    for addr, value in slave.input_registers.items():
                        conn.execute('''
                            INSERT INTO slave_data 
                            (slave_id, slave_name, register_type, register_address, register_value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (slave_id, slave.name, 'input', addr, value))
                    
                    # Recolectar coils
                    for addr, value in slave.coils.items():
                        conn.execute('''
                            INSERT INTO slave_data 
                            (slave_id, slave_name, register_type, register_address, register_value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (slave_id, slave.name, 'coil', addr, int(value)))
                    
                    # Recolectar discrete inputs
                    for addr, value in slave.discrete_inputs.items():
                        conn.execute('''
                            INSERT INTO slave_data 
                            (slave_id, slave_name, register_type, register_address, register_value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (slave_id, slave.name, 'discrete', addr, int(value)))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error collecting slave data: {e}")
    
    def collect_statistics(self):
        """Recolectar estadísticas de los esclavos"""
        try:
            with self.get_db_connection() as conn:
                for slave_id, stats in self.modbus_server.stats.items():
                    last_request_time = None
                    if stats.last_request_time > 0:
                        last_request_time = datetime.fromtimestamp(stats.last_request_time)
                    
                    conn.execute('''
                        INSERT INTO slave_statistics 
                        (slave_id, total_requests, successful_requests, failed_requests, 
                         bytes_sent, bytes_received, last_request_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (slave_id, stats.total_requests, stats.successful_requests,
                          stats.failed_requests, stats.bytes_sent, stats.bytes_received,
                          last_request_time))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error collecting statistics: {e}")
    
    def cleanup_old_data(self):
        """Limpiar datos antiguos según la configuración de retención"""
        try:
            cutoff_date = datetime.now() - timedelta(days=WEB_SERVER_CONFIG['data_retention_days'])
            
            with self.get_db_connection() as conn:
                # Limpiar datos antiguos
                conn.execute('DELETE FROM slave_data WHERE timestamp < ?', (cutoff_date,))
                conn.execute('DELETE FROM slave_statistics WHERE timestamp < ?', (cutoff_date,))
                conn.execute('DELETE FROM system_events WHERE timestamp < ?', (cutoff_date,))
                
                # Optimizar base de datos
                conn.execute('VACUUM')
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def log_system_event(self, event_type: str, description: str, severity: str = 'INFO'):
        """Registrar evento del sistema"""
        try:
            with self.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO system_events (event_type, event_description, severity)
                    VALUES (?, ?, ?)
                ''', (event_type, description, severity))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging system event: {e}")
    
    def run(self):
        """Ejecutar el servidor web"""
        try:
            # Crear directorios necesarios
            os.makedirs(WEB_SERVER_CONFIG['static_folder'], exist_ok=True)
            os.makedirs(WEB_SERVER_CONFIG['template_folder'], exist_ok=True)
            
            self.logger.info(f"Starting web server on {WEB_SERVER_CONFIG['host']}:{WEB_SERVER_CONFIG['port']}")
            
            self.app.run(
                host=WEB_SERVER_CONFIG['host'],
                port=WEB_SERVER_CONFIG['port'],
                debug=WEB_SERVER_CONFIG['debug'],
                threaded=WEB_SERVER_CONFIG['threaded']
            )
            
        except Exception as e:
            self.logger.error(f"Error starting web server: {e}")
            raise


def main():
    """Función principal"""
    print("Modbus Web Server for Raspberry Pi Zero 2W")
    print("=" * 50)
    
    try:
        # Crear servidor web
        web_server = ModbusWebServer()
        
        # Crear templates y archivos estáticos si no existen
        create_web_assets()
        
        print(f"Web server starting on http://0.0.0.0:{WEB_SERVER_CONFIG['port']}")
        print("Access the dashboard at: http://[pi-ip-address]:8080")
        print("Press Ctrl+C to stop")
        
        # Ejecutar servidor web
        web_server.run()
        
    except KeyboardInterrupt:
        print("\nShutting down web server...")
    except Exception as e:
        print(f"Error: {e}")


def create_web_assets():
    """Crear archivos web necesarios si no existen"""
    # Esta función se implementará en el siguiente archivo
    pass


if __name__ == "__main__":
    main()
