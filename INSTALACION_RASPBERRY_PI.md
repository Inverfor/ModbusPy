# Instalación del Servidor Modbus Industrial en Raspberry Pi Zero 2W

## Guía Completa de Instalación y Configuración

### Requisitos Previos

#### Hardware Necesario:
- Raspberry Pi Zero 2W
- Tarjeta microSD (mínimo 16GB, recomendado 32GB)
- Adaptador USB-to-Serial (para comunicación Modbus RTU)
- Fuente de alimentación 5V/2.5A
- Conexión a red (WiFi o Ethernet con adaptador)

#### Software Base:
- Raspberry Pi OS Lite (Bullseye o superior)
- Python 3.9+
- Acceso SSH habilitado

---

## Paso 1: Preparación del Sistema

### 1.1 Actualizar el Sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 1.2 Instalar Dependencias del Sistema
```bash
# Herramientas básicas
sudo apt install -y git python3-pip python3-venv python3-dev

# Dependencias para interfaces gráficas
sudo apt install -y python3-tk python3-matplotlib

# Herramientas de desarrollo
sudo apt install -y build-essential cmake

# Utilidades del sistema
sudo apt install -y htop nano curl wget
```

### 1.3 Configurar Puerto Serie (si es necesario)
```bash
# Habilitar UART
sudo raspi-config
# Seleccionar: 3 Interface Options -> P6 Serial Port
# Login shell over serial: No
# Serial port hardware enabled: Yes

# Agregar usuario al grupo dialout
sudo usermod -a -G dialout $USER

# Reiniciar para aplicar cambios
sudo reboot
```

---

## Paso 2: Instalación del Aplicativo

### 2.1 Crear Directorio del Proyecto
```bash
# Crear directorio principal
mkdir -p ~/modbus_server
cd ~/modbus_server

# Crear estructura de directorios
mkdir -p templates static/css static/js static/img logs backups
```

### 2.2 Crear Entorno Virtual Python
```bash
# Crear entorno virtual
python3 -m venv modbus_env

# Activar entorno virtual
source modbus_env/bin/activate

# Actualizar pip
pip install --upgrade pip
```

### 2.3 Instalar Dependencias Python
```bash
# Dependencias principales
pip install flask==2.3.3
pip install pyserial==3.5
pip install psutil==5.9.5

# Dependencias opcionales para gráficos (si se necesitan en servidor)
pip install matplotlib==3.7.2
pip install numpy==1.24.3

# Crear archivo requirements.txt
cat > requirements.txt << EOF
flask==2.3.3
pyserial==3.5
psutil==5.9.5
matplotlib==3.7.2
numpy==1.24.3
EOF
```

### 2.4 Transferir Archivos del Proyecto

#### Opción A: Usando SCP (desde tu PC)
```bash
# Desde tu PC Windows (usar PowerShell o WSL)
scp modbus_industrial_server.py pi@[IP_DEL_PI]:~/modbus_server/
scp modbus_web_server.py pi@[IP_DEL_PI]:~/modbus_server/
scp modbus_server_config.json pi@[IP_DEL_PI]:~/modbus_server/
scp -r templates pi@[IP_DEL_PI]:~/modbus_server/
scp -r static pi@[IP_DEL_PI]:~/modbus_server/
```

#### Opción B: Crear archivos directamente en el Pi
```bash
# En el Raspberry Pi, crear cada archivo usando nano
nano modbus_industrial_server.py
# Copiar y pegar el contenido del archivo

nano modbus_web_server.py
# Copiar y pegar el contenido del archivo

nano modbus_server_config.json
# Copiar y pegar el contenido del archivo

# Crear templates
nano templates/base.html
nano templates/dashboard.html
nano templates/slaves.html
nano templates/charts.html
nano templates/config.html

# Crear archivos JavaScript y CSS
nano static/js/app.js
```

---

## Paso 3: Configuración del Sistema

### 3.1 Configurar Permisos
```bash
# Hacer ejecutables los scripts Python
chmod +x ~/modbus_server/modbus_industrial_server.py
chmod +x ~/modbus_server/modbus_web_server.py

# Configurar permisos para logs
sudo mkdir -p /var/log/modbus
sudo chown pi:pi /var/log/modbus

# Configurar permisos para backups
sudo mkdir -p /var/backups/modbus
sudo chown pi:pi /var/backups/modbus
```

### 3.2 Configurar Firewall (opcional pero recomendado)
```bash
# Instalar UFW si no está instalado
sudo apt install -y ufw

# Configurar reglas básicas
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH
sudo ufw allow ssh

# Permitir puerto del servidor web
sudo ufw allow 8080/tcp

# Habilitar firewall
sudo ufw --force enable
```

### 3.3 Optimizaciones para Pi Zero 2W
```bash
# Configurar governor de CPU para rendimiento
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Hacer permanente la configuración de CPU
echo 'echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor' | sudo tee -a /etc/rc.local

# Configurar memoria virtual
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Optimizar I/O para tarjeta SD
echo 'deadline' | sudo tee /sys/block/mmcblk0/queue/scheduler
```

---

## Paso 4: Configuración como Servicio del Sistema

### 4.1 Crear Servicio para el Servidor Modbus
```bash
sudo nano /etc/systemd/system/modbus-server.service
```

Contenido del archivo:
```ini
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
```

### 4.2 Crear Servicio para el Servidor Web
```bash
sudo nano /etc/systemd/system/modbus-web.service
```

Contenido del archivo:
```ini
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
```

### 4.3 Habilitar y Iniciar Servicios
```bash
# Recargar configuración de systemd
sudo systemctl daemon-reload

# Habilitar servicios para inicio automático
sudo systemctl enable modbus-server.service
sudo systemctl enable modbus-web.service

# Iniciar servicios
sudo systemctl start modbus-server.service
sudo systemctl start modbus-web.service

# Verificar estado
sudo systemctl status modbus-server.service
sudo systemctl status modbus-web.service
```

---

## Paso 5: Verificación y Pruebas

### 5.1 Verificar Servicios
```bash
# Ver logs del servidor Modbus
sudo journalctl -u modbus-server.service -f

# Ver logs del servidor web
sudo journalctl -u modbus-web.service -f

# Verificar puertos abiertos
sudo netstat -tlnp | grep :8080
```

### 5.2 Pruebas de Conectividad
```bash
# Obtener IP del Raspberry Pi
hostname -I

# Probar servidor web localmente
curl http://localhost:8080

# Verificar temperatura del CPU
vcgencmd measure_temp

# Verificar uso de recursos
htop
```

### 5.3 Acceso desde la Red Local
```bash
# Desde tu PC, abrir navegador web:
http://[IP_DEL_RASPBERRY_PI]:8080
```

---

## Paso 6: Configuración de Red y Acceso Remoto

### 6.1 Configurar IP Estática (opcional)
```bash
sudo nano /etc/dhcpcd.conf
```

Agregar al final:
```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

### 6.2 Configurar SSH para Acceso Remoto
```bash
# Generar claves SSH (opcional, para mayor seguridad)
ssh-keygen -t rsa -b 4096

# Configurar SSH
sudo nano /etc/ssh/sshd_config

# Cambiar configuraciones recomendadas:
# Port 22 (o cambiar por otro puerto)
# PermitRootLogin no
# PasswordAuthentication yes (o no si usas claves)

# Reiniciar SSH
sudo systemctl restart ssh
```

---

## Paso 7: Monitoreo y Mantenimiento

### 7.1 Scripts de Monitoreo
```bash
# Crear script de monitoreo
nano ~/monitor_system.sh
```

Contenido:
```bash
#!/bin/bash
echo "=== Sistema Modbus Industrial ==="
echo "Fecha: $(date)"
echo "Temperatura CPU: $(vcgencmd measure_temp)"
echo "Uso de memoria: $(free -h | grep Mem)"
echo "Uso de CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)"
echo "Estado servicios:"
systemctl is-active modbus-server.service
systemctl is-active modbus-web.service
echo "Conexiones activas:"
netstat -an | grep :8080 | wc -l
```

```bash
chmod +x ~/monitor_system.sh
```

### 7.2 Configurar Rotación de Logs
```bash
sudo nano /etc/logrotate.d/modbus-server
```

Contenido:
```
/var/log/modbus/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
```

### 7.3 Script de Backup Automático
```bash
nano ~/backup_modbus.sh
```

Contenido:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/modbus"
DATE=$(date +%Y%m%d_%H%M%S)

# Crear backup de configuración
tar -czf "$BACKUP_DIR/modbus_config_$DATE.tar.gz" \
    ~/modbus_server/modbus_server_config.json \
    ~/modbus_server/modbus_data.db

# Mantener solo los últimos 10 backups
ls -t $BACKUP_DIR/modbus_config_*.tar.gz | tail -n +11 | xargs -r rm

echo "Backup completado: modbus_config_$DATE.tar.gz"
```

```bash
chmod +x ~/backup_modbus.sh

# Agregar a crontab para backup diario
crontab -e
# Agregar línea:
# 0 2 * * * /home/pi/backup_modbus.sh
```

---

## Paso 8: Solución de Problemas Comunes

### 8.1 Problemas de Permisos
```bash
# Si hay problemas con puertos serie
sudo usermod -a -G dialout pi
sudo reboot

# Si hay problemas con archivos
sudo chown -R pi:pi ~/modbus_server
chmod -R 755 ~/modbus_server
```

### 8.2 Problemas de Memoria
```bash
# Verificar uso de memoria
free -h

# Configurar swap si es necesario
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Cambiar CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 8.3 Problemas de Red
```bash
# Verificar conectividad
ping google.com

# Verificar configuración de red
ip addr show

# Reiniciar servicios de red
sudo systemctl restart networking
```

### 8.4 Comandos Útiles de Diagnóstico
```bash
# Ver logs en tiempo real
sudo journalctl -f

# Verificar servicios
sudo systemctl list-units --failed

# Verificar temperatura
watch -n 1 vcgencmd measure_temp

# Verificar procesos
ps aux | grep python

# Verificar puertos
sudo ss -tlnp
```

---

## Acceso Final

Una vez completada la instalación:

1. **Acceso Web**: `http://[IP_DEL_PI]:8080`
2. **SSH**: `ssh pi@[IP_DEL_PI]`
3. **Logs**: `sudo journalctl -u modbus-web.service -f`
4. **Monitoreo**: `~/monitor_system.sh`

## URLs de Acceso:
- Dashboard: `http://[IP_DEL_PI]:8080/`
- Gestión de Esclavos: `http://[IP_DEL_PI]:8080/slaves`
- Gráficos: `http://[IP_DEL_PI]:8080/charts`
- Configuración: `http://[IP_DEL_PI]:8080/config`

¡El servidor Modbus Industrial está listo para uso en producción!
