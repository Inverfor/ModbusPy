# Modbus RTU Industrial Server para Raspberry Pi Zero 2W

## Descripción

Este es un servidor Modbus RTU industrial completo, optimizado específicamente para Raspberry Pi Zero 2W. Diseñado para aplicaciones industriales que requieren alta confiabilidad, monitoreo en tiempo real y características de nivel empresarial.

## Características Principales

### 🚀 Optimizado para Pi Zero 2W
- **Gestión eficiente de memoria**: Optimizado para 512MB RAM
- **Uso inteligente de CPU**: Aprovecha los 4 núcleos ARM Cortex-A53
- **Monitoreo de rendimiento**: Control automático de temperatura y recursos
- **Configuración específica**: Parámetros ajustados para el hardware

### 🏭 Características Industriales
- **Multi-slave RTU**: Soporte para múltiples dispositivos esclavos
- **Logging robusto**: Sistema de logs rotativo con niveles configurables
- **Reconexión automática**: Recuperación automática de errores de comunicación
- **Estadísticas en tiempo real**: Monitoreo completo de rendimiento
- **Respaldo automático**: Configuración y datos respaldados automáticamente

### 📡 Protocolos Modbus Soportados
- **Función 01h**: Read Coils
- **Función 02h**: Read Discrete Inputs
- **Función 03h**: Read Holding Registers
- **Función 04h**: Read Input Registers
- **Función 05h**: Write Single Coil
- **Función 06h**: Write Single Register
- **Función 0Fh**: Write Multiple Coils
- **Función 10h**: Write Multiple Registers
- **Función 14h**: Read File Records

### 🖥️ Interfaz de Monitoreo
- **GUI de diagnósticos**: Interfaz gráfica completa para monitoreo
- **Gráficos en tiempo real**: CPU, memoria, temperatura y tráfico
- **Gestión de esclavos**: Agregar, remover y configurar dispositivos
- **Visualización de estadísticas**: Métricas detalladas por esclavo
- **Editor de configuración**: Modificación en vivo de parámetros

## Instalación

### Requisitos del Sistema
```bash
# Raspberry Pi OS (Bullseye o superior)
# Python 3.9+
# Dependencias del sistema
sudo apt update
sudo apt install python3-pip python3-venv git

# Para la interfaz gráfica
sudo apt install python3-tk python3-matplotlib
```

### Instalación de Dependencias Python
```bash
# Crear entorno virtual
python3 -m venv modbus_env
source modbus_env/bin/activate

# Instalar dependencias
pip install pyserial psutil matplotlib numpy
```

### Configuración del Sistema
```bash
# Habilitar puerto serie (si es necesario)
sudo raspi-config
# Interfacing Options -> Serial -> No (login shell) -> Yes (serial port hardware)

# Agregar usuario al grupo dialout
sudo usermod -a -G dialout $USER

# Reiniciar para aplicar cambios
sudo reboot
```

## Configuración

### Archivo de Configuración Principal
El servidor utiliza `modbus_server_config.json` para su configuración:

```json
{
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
        "auto_optimize": true
    },
    "pi_zero_optimization": {
        "enable_cpu_governor": true,
        "cpu_governor": "performance",
        "enable_memory_optimization": true,
        "swap_usage_threshold": 50,
        "temperature_threshold": 70,
        "throttle_on_overheat": true
    },
    "industrial_features": {
        "enable_watchdog": true,
        "watchdog_timeout": 30,
        "enable_backup": true,
        "backup_directory": "/var/backups/modbus",
        "enable_redundancy": false,
        "redundant_port": "/dev/ttyUSB1"
    }
}
```

### Configuración de Puertos Serie
```bash
# Verificar puertos disponibles
ls -la /dev/tty*

# Para USB-to-Serial adapters
/dev/ttyUSB0, /dev/ttyUSB1, etc.

# Para GPIO UART
/dev/ttyAMA0 (Pi Zero 2W)
```

## Uso

### 1. Servidor Básico por Línea de Comandos
```bash
# Ejecutar servidor con configuración por defecto
python3 modbus_industrial_server.py
```

### 2. Interfaz Gráfica de Diagnósticos
```bash
# Ejecutar interfaz de monitoreo
python3 modbus_diagnostics.py
```

### 3. Integración con Código Existente
```python
from modbus_industrial_server import ModbusIndustrialServer, SlaveConfig

# Crear servidor
server = ModbusIndustrialServer("mi_config.json")

# Configurar esclavo personalizado
slave_config = SlaveConfig(
    slave_id=1,
    name="Sensor de Temperatura",
    description="Sensor industrial PT100",
    holding_registers={
        2001: 2500,  # Temperatura * 100
        2002: 1013,  # Presión atmosférica
    },
    input_registers={
        3001: 25,    # Temperatura actual
        3002: 60,    # Humedad relativa
    },
    coils={
        1: True,     # Calefactor activo
        2: False,    # Alarma
    },
    discrete_inputs={
        10001: True, # Sensor conectado
        10002: False # Falla de comunicación
    },
    file_records={
        1: {
            0: b"SENSOR_TEMP_V2.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            1: b"SN_987654321\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        }
    }
)

# Agregar esclavo al servidor
server.add_slave(slave_config)

# Iniciar servidor
server.start_server()

# Mantener servidor activo
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop_server()
```

## Características Avanzadas

### Monitoreo de Rendimiento
```python
# Acceder a estadísticas en tiempo real
stats = server.get_slave_data(slave_id=1)
print(f"Requests totales: {stats['statistics']['total_requests']}")
print(f"Tasa de éxito: {stats['statistics']['successful_requests']}")
```

### Actualización Dinámica de Registros
```python
# Actualizar valores de registros en tiempo real
server.update_register(slave_id=1, register_type='holding', address=2001, value=2750)
server.update_register(slave_id=1, register_type='coil', address=1, value=False)
```

### Logging Personalizado
```python
import logging

# Configurar logging personalizado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mi_aplicacion.log'),
        logging.StreamHandler()
    ]
)
```

## Optimizaciones para Pi Zero 2W

### Configuración del Sistema
```bash
# Optimizar governor de CPU
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Configurar memoria
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Optimizar I/O
echo 'deadline' | sudo tee /sys/block/mmcblk0/queue/scheduler
```

### Configuración de Red (opcional)
```bash
# Para acceso remoto al servidor
sudo ufw allow 502/tcp  # Puerto Modbus TCP (si se implementa)
sudo ufw allow 22/tcp   # SSH para administración remota
```

## Solución de Problemas

### Problemas Comunes

#### 1. Error de Permisos en Puerto Serie
```bash
# Solución
sudo usermod -a -G dialout $USER
sudo reboot
```

#### 2. Puerto Serie No Disponible
```bash
# Verificar puertos
dmesg | grep tty
ls -la /dev/ttyUSB*

# Verificar conexión USB
lsusb
```

#### 3. Memoria Insuficiente
```bash
# Verificar uso de memoria
free -h
htop

# Configurar swap si es necesario
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### 4. Sobrecalentamiento
```bash
# Verificar temperatura
vcgencmd measure_temp

# Configurar throttling
echo 'arm_freq=800' | sudo tee -a /boot/config.txt
```

### Logs de Diagnóstico
```bash
# Ver logs del servidor
tail -f /var/log/modbus_server.log

# Ver logs del sistema
journalctl -u modbus-server -f

# Verificar rendimiento
htop
iotop
```

## Instalación como Servicio del Sistema

### Crear Servicio Systemd
```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/modbus-server.service
```

```ini
[Unit]
Description=Modbus Industrial Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/modbus_server
ExecStart=/home/pi/modbus_server/modbus_env/bin/python /home/pi/modbus_server/modbus_industrial_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable modbus-server
sudo systemctl start modbus-server

# Verificar estado
sudo systemctl status modbus-server
```

## Estructura de Archivos

```
modbus_server/
├── modbus_industrial_server.py    # Servidor principal
├── modbus_diagnostics.py          # Interfaz de diagnósticos
├── modbus_server_config.json      # Configuración principal
├── modbus_gui.py                   # GUI cliente existente
├── test.py                         # Pruebas básicas
├── file_record_test.py            # Pruebas de file records
├── README_Modbus_Industrial_Server.md  # Esta documentación
└── logs/                          # Directorio de logs
    ├── modbus_server.log
    └── performance.log
```

## Ejemplos de Integración

### Integración con InfluxDB
```python
from influxdb import InfluxDBClient

def log_to_influxdb(slave_data):
    client = InfluxDBClient('localhost', 8086, 'user', 'pass', 'modbus_db')
    
    json_body = [
        {
            "measurement": "modbus_data",
            "tags": {
                "slave_id": slave_data['slave_id'],
                "slave_name": slave_data['name']
            },
            "fields": {
                "total_requests": slave_data['statistics']['total_requests'],
                "success_rate": slave_data['statistics']['successful_requests']
            }
        }
    ]
    
    client.write_points(json_body)
```

### Integración con MQTT
```python
import paho.mqtt.client as mqtt
import json

def publish_to_mqtt(slave_data):
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)
    
    topic = f"modbus/slave/{slave_data['slave_id']}"
    payload = json.dumps(slave_data['holding_registers'])
    
    client.publish(topic, payload)
    client.disconnect()
```

## Rendimiento y Benchmarks

### Especificaciones Típicas en Pi Zero 2W
- **Throughput**: ~100-500 requests/segundo (dependiendo de la configuración)
- **Latencia**: <10ms para requests simples
- **Memoria**: ~50-100MB de uso típico
- **CPU**: 10-30% de uso promedio
- **Temperatura**: Operación estable hasta 70°C

### Optimizaciones de Rendimiento
```python
# Configuración para máximo rendimiento
PI_ZERO_CONFIG = {
    'max_threads': 4,           # Usar todos los núcleos
    'memory_limit_mb': 400,     # Límite de memoria conservador
    'cpu_threshold': 80,        # Umbral de CPU
    'max_connections': 10,      # Conexiones concurrentes
    'buffer_size': 2048,        # Buffer más grande
    'response_timeout': 3.0,    # Timeout optimizado
}
```

## Licencia y Soporte

Este software está diseñado para uso industrial y educativo. Para soporte técnico o consultas sobre implementaciones específicas, consulte la documentación técnica o contacte al desarrollador.

## Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Cree una rama para su feature
3. Commit sus cambios
4. Push a la rama
5. Cree un Pull Request

## Changelog

### v1.0.0 (2024)
- Implementación inicial del servidor Modbus RTU
- Soporte completo para Pi Zero 2W
- Interfaz de diagnósticos
- Sistema de logging industrial
- Monitoreo de rendimiento en tiempo real
- Soporte para múltiples esclavos
- Configuración JSON flexible
