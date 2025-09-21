#!/bin/bash

# Script de Instalación Automática del Servidor Modbus Industrial
# Para Raspberry Pi Zero 2W
# Versión: 1.0

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para verificar si el comando fue exitoso
check_command() {
    if [ $? -eq 0 ]; then
        print_success "$1"
    else
        print_error "Falló: $1"
        exit 1
    fi
}

# Banner de inicio
echo -e "${BLUE}"
echo "=================================================="
echo "  Instalador Servidor Modbus Industrial"
echo "  Optimizado para Raspberry Pi Zero 2W"
echo "  Versión 1.0"
echo "=================================================="
echo -e "${NC}"

# Verificar si se ejecuta como usuario pi
if [ "$USER" != "pi" ]; then
    print_warning "Se recomienda ejecutar este script como usuario 'pi'"
    read -p "¿Continuar de todos modos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Paso 1: Actualizar sistema
print_status "Actualizando sistema..."
sudo apt update && sudo apt upgrade -y
check_command "Actualización del sistema"

# Paso 2: Instalar dependencias del sistema
print_status "Instalando dependencias del sistema..."
sudo apt install -y git python3-pip python3-venv python3-dev python3-tk python3-matplotlib build-essential cmake htop nano curl wget ufw
check_command "Instalación de dependencias del sistema"

# Paso 3: Configurar usuario para puerto serie
print_status "Configurando permisos para puerto serie..."
sudo usermod -a -G dialout $USER
check_command "Configuración de permisos serie"

# Paso 4: Crear estructura de directorios
print_status "Creando estructura de directorios..."
mkdir -p ~/modbus_server/{templates,static/{css,js,img},logs,backups}
check_command "Creación de directorios"

# Paso 5: Crear entorno virtual Python
print_status "Creando entorno virtual Python..."
cd ~/modbus_server
python3 -m venv modbus_env
check_command "Creación de entorno virtual"

# Activar entorno virtual
source modbus_env/bin/activate
check_command "Activación de entorno virtual"

# Paso 6: Instalar dependencias Python
print_status "Instalando dependencias Python..."
pip install --upgrade pip
pip install flask==2.3.3 pyserial==3.5 psutil==5.9.5 matplotlib==3.7.2 numpy==1.24.3
check_command "Instalación de dependencias Python"

# Crear requirements.txt
cat > requirements.txt << EOF
flask==2.3.3
pyserial==3.5
psutil==5.9.5
matplotlib==3.7.2
numpy==1.24.3
EOF

# Paso 7: Configurar permisos del sistema
print_status "Configurando permisos del sistema..."
sudo mkdir -p /var/log/modbus /var/backups/modbus
sudo chown pi:pi /var/log/modbus /var/backups/modbus
check_command "Configuración de permisos del sistema"

# Paso 8: Configurar firewall
print_status "Configurando firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp
sudo ufw --force enable
check_command "Configuración de firewall"

# Paso 9: Optimizaciones para Pi Zero 2W
print_status "Aplicando optimizaciones para Pi Zero 2W..."

# Configurar CPU governor
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null

# Hacer permanente la configuración de CPU
if ! grep -q "scaling_governor" /etc/rc.local; then
    sudo sed -i '/^exit 0/i echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null' /etc/rc.local
fi

# Configurar memoria virtual
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf > /dev/null
fi

# Optimizar I/O
echo 'deadline' | sudo tee /sys/block/mmcblk0/queue/scheduler > /dev/null

check_command "Optimizaciones del sistema"

# Paso 10: Crear servicios systemd
print_status "Creando servicios del sistema..."

# Servicio Modbus Server
sudo tee /etc/systemd/system/modbus-server.service > /dev/null << EOF
[Unit]
Description=Modbus Industrial Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/modbus_server
Environment=PATH=/home/pi/modbus_server/modbus_env/bin
ExecStart=/home/pi/modbus_server/modbus_env/bin/python /home/pi/modbus_server/modbus_industrial_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Servicio Web Server
sudo tee /etc/systemd/system/modbus-web.service > /dev/null << EOF
[Unit]
Description=Modbus Web Server
After=network.target modbus-server.service
Wants=network.target
Requires=modbus-server.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/modbus_server
Environment=PATH=/home/pi/modbus_server/modbus_env/bin
ExecStart=/home/pi/modbus_server/modbus_env/bin/python /home/pi/modbus_server/modbus_web_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
check_command "Creación de servicios del sistema"

# Paso 11: Crear scripts de utilidad
print_status "Creando scripts de utilidad..."

# Script de monitoreo
tee ~/monitor_system.sh > /dev/null << 'EOF'
#!/bin/bash
echo "=== Sistema Modbus Industrial ==="
echo "Fecha: $(date)"
echo "Temperatura CPU: $(vcgencmd measure_temp)"
echo "Uso de memoria: $(free -h | grep Mem)"
echo "Uso de CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "Estado servicios:"
echo "  Modbus Server: $(systemctl is-active modbus-server.service)"
echo "  Web Server: $(systemctl is-active modbus-web.service)"
echo "Conexiones activas en puerto 8080: $(netstat -an 2>/dev/null | grep :8080 | wc -l)"
echo "IP del sistema: $(hostname -I)"
EOF

chmod +x ~/monitor_system.sh

# Script de backup
tee ~/backup_modbus.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/modbus"
DATE=$(date +%Y%m%d_%H%M%S)

# Crear backup de configuración
tar -czf "$BACKUP_DIR/modbus_config_$DATE.tar.gz" \
    ~/modbus_server/modbus_server_config.json \
    ~/modbus_server/modbus_data.db 2>/dev/null

# Mantener solo los últimos 10 backups
ls -t $BACKUP_DIR/modbus_config_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm

echo "Backup completado: modbus_config_$DATE.tar.gz"
EOF

chmod +x ~/backup_modbus.sh

check_command "Creación de scripts de utilidad"

# Paso 12: Configurar rotación de logs
print_status "Configurando rotación de logs..."
sudo tee /etc/logrotate.d/modbus-server > /dev/null << EOF
/var/log/modbus/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

check_command "Configuración de rotación de logs"

# Paso 13: Crear archivo de configuración por defecto
print_status "Creando configuración por defecto..."
tee ~/modbus_server/modbus_server_config.json > /dev/null << 'EOF'
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
        "log_file": "/var/log/modbus/modbus_server.log",
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
    },
    "web_server": {
        "host": "0.0.0.0",
        "port": 8080,
        "data_retention_days": 30,
        "sampling_interval": 5
    }
}
EOF

check_command "Creación de configuración por defecto"

# Paso 14: Mostrar información final
print_success "¡Instalación completada exitosamente!"

echo
echo -e "${YELLOW}PRÓXIMOS PASOS:${NC}"
echo "1. Transferir los archivos Python del proyecto:"
echo "   - modbus_industrial_server.py"
echo "   - modbus_web_server.py"
echo "   - templates/ (directorio completo)"
echo "   - static/ (directorio completo)"
echo
echo "2. Habilitar e iniciar los servicios:"
echo "   sudo systemctl enable modbus-server.service"
echo "   sudo systemctl enable modbus-web.service"
echo "   sudo systemctl start modbus-server.service"
echo "   sudo systemctl start modbus-web.service"
echo
echo "3. Verificar el estado:"
echo "   ~/monitor_system.sh"
echo
echo "4. Acceder al servidor web:"
echo "   http://$(hostname -I | awk '{print $1}'):8080"
echo
echo -e "${GREEN}ARCHIVOS CREADOS:${NC}"
echo "- ~/modbus_server/ (directorio principal)"
echo "- ~/monitor_system.sh (script de monitoreo)"
echo "- ~/backup_modbus.sh (script de backup)"
echo "- /etc/systemd/system/modbus-*.service (servicios del sistema)"
echo
echo -e "${BLUE}COMANDOS ÚTILES:${NC}"
echo "- Ver logs: sudo journalctl -u modbus-web.service -f"
echo "- Estado servicios: sudo systemctl status modbus-server.service"
echo "- Monitoreo: ~/monitor_system.sh"
echo "- Backup: ~/backup_modbus.sh"
echo
print_warning "IMPORTANTE: Reinicie el sistema para aplicar todos los cambios:"
echo "sudo reboot"
