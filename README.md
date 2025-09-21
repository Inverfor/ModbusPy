# Modbus Web Server para Raspberry Pi Zero 2W

## Descripción

Servidor web industrial completo para monitoreo y control de dispositivos Modbus RTU, optimizado específicamente para Raspberry Pi Zero 2W. Incluye interfaz web moderna, almacenamiento de datos históricos y características de nivel empresarial.

## Características Principales

### 🚀 Optimizado para Pi Zero 2W
- **Gestión eficiente de memoria**: Optimizado para 512MB RAM
- **Uso inteligente de CPU**: Aprovecha los 4 núcleos ARM Cortex-A53
- **Monitoreo de rendimiento**: Control automático de temperatura y recursos
- **Configuración específica**: Parámetros ajustados para el hardware

### 🌐 Interfaz Web Moderna
- **Dashboard en tiempo real**: Monitoreo visual de todos los esclavos
- **Gráficos interactivos**: Tendencias históricas y datos en tiempo real
- **Gestión de esclavos**: Configuración y control desde la web
- **API RESTful**: Acceso programático a todos los datos
- **Responsive Design**: Compatible con móviles y tablets

### 🏭 Características Industriales
- **Multi-slave RTU**: Soporte para múltiples dispositivos esclavos
- **Base de datos SQLite**: Almacenamiento eficiente de datos históricos
- **Logging robusto**: Sistema de logs rotativo con niveles configurables
- **Reconexión automática**: Recuperación automática de errores de comunicación
- **Estadísticas en tiempo real**: Monitoreo completo de rendimiento

### 📡 Protocolos Modbus Soportados
- **Función 01h**: Read Coils
- **Función 02h**: Read Discrete Inputs
- **Función 03h**: Read Holding Registers
- **Función 04h**: Read Input Registers
- **Función 05h**: Write Single Coil
- **Función 06h**: Write Single Register
- **Función 0Fh**: Write Multiple Coils
- **Función 10h**: Write Multiple Registers

## Estructura del Proyecto

```
modbus_web_server/
├── modbus_web_server.py           # Servidor web principal (Flask)
├── modbus_industrial_server.py    # Servidor Modbus RTU
├── modbus_diagnostics.py          # Interfaz de diagnósticos GUI
├── modbus_gui.py                   # Cliente GUI para pruebas
├── modbus_server_config.json      # Configuración principal
├── install_script.sh              # Script de instalación automática
├── INSTALACION_RASPBERRY_PI.md    # Guía de instalación detallada
├── README_Modbus_Industrial_Server.md  # Documentación del servidor Modbus
├── templates/                      # Plantillas HTML
│   ├── base.html
│   ├── dashboard.html
│   ├── slaves.html
│   ├── charts.html
│   └── config.html
└── static/                         # Archivos estáticos (CSS, JS, imágenes)
    ├── css/
    ├── js/
    │   └── app.js
    └── img/
```

## Instalación Rápida

### Opción 1: Script Automático
```bash
# Descargar y ejecutar script de instalación
wget https://raw.githubusercontent.com/tu-repo/modbus-web-server/main/install_script.sh
chmod +x install_script.sh
sudo ./install_script.sh
```

### Opción 2: Instalación Manual
```bash
# Clonar repositorio
git clone https://github.com/tu-repo/modbus-web-server.git
cd modbus-web-server

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install flask pyserial psutil sqlite3

# Configurar permisos de puerto serie
sudo usermod -a -G dialout inverforZeroUbuntu
sudo reboot
```

## Uso

### 1. Iniciar Servidor Web
```bash
# Activar entorno virtual
source /home/inverforZeroUbuntu/modbus_server/modbus_env/bin/activate

# Ejecutar servidor web
python3 modbus_web_server.py
```

### 2. Acceder a la Interfaz Web
- Abrir navegador en: `http://[ip-del-pi]:8080`
- Dashboard principal: `http://[ip-del-pi]:8080/`
- Gestión de esclavos: `http://[ip-del-pi]:8080/slaves`
- Gráficos: `http://[ip-del-pi]:8080/charts`
- Configuración: `http://[ip-del-pi]:8080/config`

### 3. API REST
```bash
# Obtener lista de esclavos
curl http://[ip-del-pi]:8080/api/slaves

# Obtener datos de un esclavo
curl http://[ip-del-pi]:8080/api/slave/1

# Obtener estadísticas del sistema
curl http://[ip-del-pi]:8080/api/statistics
```

## Configuración

### Archivo de Configuración Principal
Editar `modbus_server_config.json`:

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
        "stats_interval": 60
    },
    "web_server": {
        "host": "0.0.0.0",
        "port": 8080,
        "data_retention_days": 30,
        "sampling_interval": 5
    }
}
```

### Configuración como Servicio del Sistema
```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/modbus-web-server.service
```

```ini
[Unit]
Description=Modbus Web Server
After=network.target

[Service]
Type=simple
User=inverforZeroUbuntu
WorkingDirectory=/home/inverforZeroUbuntu/modbus_server
ExecStart=/home/inverforZeroUbuntu/modbus_server/modbus_env/bin/python /home/inverforZeroUbuntu/modbus_server/modbus_web_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable modbus-web-server
sudo systemctl start modbus-web-server
```

## Características de la Interfaz Web

### Dashboard Principal
- Vista general de todos los esclavos conectados
- Estado en tiempo real de cada dispositivo
- Métricas de rendimiento del sistema
- Alertas y notificaciones

### Gestión de Esclavos
- Agregar/remover esclavos dinámicamente
- Configurar registros y direcciones
- Monitorear estado de comunicación
- Actualizar valores de registros

### Gráficos y Tendencias
- Visualización de datos históricos
- Gráficos interactivos con zoom
- Exportación de datos
- Configuración de intervalos de tiempo

### Configuración del Sistema
- Parámetros de comunicación serie
- Configuración de esclavos
- Ajustes de rendimiento
- Gestión de logs

## API REST Endpoints

### Esclavos
- `GET /api/slaves` - Lista todos los esclavos
- `GET /api/slave/{id}` - Detalles de un esclavo
- `GET /api/slave/{id}/data` - Datos históricos
- `GET /api/slave/{id}/chart` - Datos para gráficos
- `POST /api/slave/{id}/update` - Actualizar registro

### Sistema
- `GET /api/statistics` - Estadísticas generales
- `GET /api/system/status` - Estado del sistema
- `POST /api/server/start` - Iniciar servidor Modbus
- `POST /api/server/stop` - Detener servidor Modbus

## Herramientas Adicionales

### Interfaz de Diagnósticos GUI
```bash
# Ejecutar interfaz de diagnósticos
python3 modbus_diagnostics.py
```

### Cliente GUI para Pruebas
```bash
# Ejecutar cliente de pruebas
python3 modbus_gui.py
```

## Optimizaciones para Pi Zero 2W

### Rendimiento Típico
- **Throughput**: ~100-500 requests/segundo
- **Latencia**: <10ms para requests simples
- **Memoria**: ~50-100MB de uso típico
- **CPU**: 10-30% de uso promedio

### Configuraciones Recomendadas
```bash
# Optimizar governor de CPU
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Configurar memoria
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Optimizar I/O
echo 'deadline' | sudo tee /sys/block/mmcblk0/queue/scheduler
```

## Solución de Problemas

### Problemas Comunes

1. **Error de permisos en puerto serie**
   ```bash
   sudo usermod -a -G dialout inverforZeroUbuntu
   sudo reboot
   ```

2. **Puerto serie no disponible**
   ```bash
   dmesg | grep tty
   ls -la /dev/ttyUSB*
   ```

3. **Servidor web no accesible**
   ```bash
   # Verificar firewall
   sudo ufw allow 8080/tcp
   
   # Verificar proceso
   ps aux | grep modbus_web_server
   ```

### Logs de Diagnóstico
```bash
# Ver logs del servidor
tail -f /var/log/modbus_server.log

# Ver logs del sistema
journalctl -u modbus-web-server -f

# Verificar base de datos
sqlite3 modbus_data.db ".tables"
```

## Desarrollo y Contribuciones

### Estructura de Desarrollo
- **Backend**: Flask + SQLite
- **Frontend**: HTML5 + CSS3 + JavaScript
- **Comunicación**: Modbus RTU sobre Serial
- **Base de datos**: SQLite para datos históricos

### Contribuir
1. Fork el repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Soporte

Para soporte técnico o consultas:
- Crear issue en GitHub
- Consultar documentación técnica
- Revisar logs del sistema

## Changelog

### v2.0.0 (2024)
- Interfaz web completa con Flask
- Base de datos SQLite para datos históricos
- API REST para integración
- Dashboard en tiempo real
- Gráficos interactivos

### v1.0.0 (2024)
- Implementación inicial del servidor Modbus RTU
- Soporte completo para Pi Zero 2W
- Interfaz de diagnósticos
- Sistema de logging industrial
