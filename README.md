# MINEBOT-Q — Hardware Layer

Sistema de adquisicion de datos ambientales para inspeccion minera subterranea.
Arduino UNO Q (STM32 + QRB2210) montado en Unitree Go2.

## Arquitectura

```
MQ-4/MQ-7/MQ-135 (ADC) ── STM32 ──UART──> QRB2210 (Docker ROS2) ──> ROS2 DDS
```

## Requisitos

- Arduino UNO Q con Debian GNU/Linux 13 (trixie)
- Docker instalado en QRB2210
- Imagen `ros:foxy-ros-base`

## Instalacion

### 1. Instalar Docker en QRB2210

```bash
ssh root@172.51.1.6
sudo apt update
sudo apt install -y docker.io
sudo docker pull ros:foxy-ros-base
```

### 2. Subir codigo al QRB2210

Desde tu PC:

```bash
mkdir -p /home/arduino/minebot_ws/src   # en el QRB2210 via SSH
scp -r hardware_layer/ arduino@172.51.1.6:/home/arduino/minebot_ws/src/
```

### 3. Crear contenedor persistente (una sola vez)

```bash
sudo docker run -d \
  --name minebot \
  --restart=always \
  --privileged \
  --net=host \
  -v /dev:/dev \
  -v /home/arduino/minebot_ws:/ros2_ws \
  -e ROS_DOMAIN_ID=42 \
  -e ROS_LOCALHOST_ONLY=0 \
  -e ROS_IP=10.95.229.127 \
  -e ROS_HOSTNAME=10.95.229.127 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  ros:foxy-ros-base \
  bash -c "apt-get update && apt-get install -y python3-colcon-common-extensions > /dev/null 2>&1 && \
           source /opt/ros/foxy/setup.bash && \
           cd /ros2_ws && colcon build --packages-select minebot_msgs && \
           source /ros2_ws/install/setup.bash && \
           stty -F /dev/ttyHS1 115200 raw -echo && \
           python3 /ros2_ws/src/hardware_layer/nodes/gas_sensor_node.py"
```

Esto crea un contenedor llamado `minebot` que:
- Instala colcon y compila `minebot_msgs` al primer arranque
- Configura el serial con `stty` antes de lanzar el nodo
- Corre `gas_sensor_node.py` automaticamente
- Se reinicia automaticamente al encender el Arduino UNO Q (`--restart=always`)

**Variables de entorno DDS:**

| Variable | Valor | Funcion |
|----------|-------|---------|
| `ROS_DOMAIN_ID` | `42` | Dominio DDS compartido con el Go2 |
| `ROS_LOCALHOST_ONLY` | `0` | Permite descubrimiento en red (no solo localhost) |
| `ROS_IP` | `10.95.229.127` | IP del QRB2210 en la red del Go2 |
| `ROS_HOSTNAME` | `10.95.229.127` | Hostname para DDS discovery |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | Middleware DDS compatible con Go2 |

### 4. Verificar que funciona

```bash
# Ver logs del contenedor
sudo docker logs -f minebot

# Entrar al contenedor para inspeccionar topicos
sudo docker exec -it minebot bash
source /opt/ros/foxy/setup.bash
export ROS_DOMAIN_ID=42
ros2 topic echo /gas/mq4
```

## Comandos utiles del contenedor

```bash
# Ver estado
sudo docker ps

# Ver logs en tiempo real
sudo docker logs -f minebot

# Reiniciar el nodo
sudo docker restart minebot

# Parar el nodo
sudo docker stop minebot

# Iniciar de nuevo
sudo docker start minebot

# Entrar al contenedor para debug
sudo docker exec -it minebot bash

# Actualizar codigo (tras scp) y reiniciar
sudo docker restart minebot

# Eliminar contenedor (si necesitas recrearlo)
sudo docker rm -f minebot
```

## Firmware STM32

Abrir `firmware/stm32_sensor_reader.ino` en Arduino IDE o PlatformIO.
Seleccionar board STM32 (Arduino UNO Q) y subir via USB (solo para flash; operacion normal usa UART interno `/dev/ttyHS1`).

## Topicos publicados

| Topico | Tipo | Frecuencia | Descripcion |
|--------|------|------------|-------------|
| `/gas/mq4` | `std_msgs/Float32` | 10 Hz | Concentracion CH4 (ppm) |
| `/gas/mq7` | `std_msgs/Float32` | 10 Hz | Concentracion CO (ppm) |
| `/gas/mq135` | `std_msgs/Float32` | 10 Hz | Calidad de aire NH3/NOx/H2S |
| `/gas/status` | `std_msgs/String` | 10 Hz | SAFE / WARNING / CRITICAL |

## Umbrales de gases — Normativa minera peruana (OSINERGMIN / DS-024-2016-EM)

| Gas | Formula | TWA (8h) | STEL (15 min) | Umbral WARNING | Umbral CRITICAL |
|-----|---------|----------|---------------|----------------|-----------------|
| Metano | CH4 | 1000 ppm (1% vol) | 2500 ppm | 500 ppm | 1000 ppm |
| Monoxido de carbono | CO | 25 ppm | 50 ppm | 50 ppm | 200 ppm |
| Calidad aire (NH3/NOx/H2S) | Varios | Variable | Variable | 200 ppm | 500 ppm |

**Referencia normativa:**
- DS-024-2016-EM: Reglamento de Seguridad y Salud Ocupacional en Mineria
- DS-023-2017-EM: Modificatoria
- OSINERGMIN: Limites de exposicion ocupacional para agentes quimicos
- Los umbrales WARNING se fijan al 50% del LEO (Limite de Exposicion Ocupacional)
- Los umbrales CRITICAL coinciden con el LEO o el STEL segun corresponda

## Parametros configurables

Editar `config/sensor_thresholds.yaml` para ajustar umbrales sin recompilar:

```yaml
gas_sensor_node:
  ros__parameters:
    serial_port: "/dev/ttyHS1"
    baud_rate: 115200
    mq4_warning_ppm: 500.0
    mq4_critical_ppm: 1000.0
    mq7_warning_ppm: 50.0
    mq7_critical_ppm: 200.0
    mq135_warning_ppm: 200.0
    mq135_critical_ppm: 500.0
```

## Estructura

```
hardware_layer/
├── firmware/
│   └── stm32_sensor_reader.ino
├── nodes/
│   └── gas_sensor_node.py
├── minebot_msgs/
│   └── msg/
│       └── Alert.msg
├── config/
│   └── sensor_thresholds.yaml
├── launch/
│   └── hardware_layer.launch.py
└── README.md
```
