# MINEBOT-Q — Hardware Layer

Sistema de adquisicion de datos ambientales para inspeccion minera subterranea.
Arduino UNO Q (STM32 + QRB2210) montado en Unitree Go2.

## Arquitectura

```
MQ-4/MQ-7/MQ-135 (ADC) ── STM32 ──UART──> QRB2210 ──> ROS2 DDS
```

## Requisitos

- Python 3.10
- ROS2 Humble Hawksbill
- pyserial

## Instalacion

```bash
# Dependencias Python
pip install pyserial

# Clonar en workspace ROS2
cd ~/ros2_ws/src
cp -r hardware_layer .
cp -r minebot_msgs .

# Build
cd ~/ros2_ws
colcon build --packages-select minebot_msgs hardware_layer

# Source
source install/setup.bash
```

## Firmware STM32

Abrir `firmware/stm32_sensor_reader.ino` en Arduino IDE o PlatformIO.
Seleccionar board STM32 (Arduino UNO Q) y subir via USB (solo para flash; operacion normal usa UART interno).

## Ejecucion

```bash
# Lanzar nodo de gas con parametros
ros2 launch hardware_layer hardware_layer.launch.py

# Verificar topicos
ros2 topic list
ros2 topic echo /gas/mq4
ros2 topic echo /gas/mq7
ros2 topic echo /gas/mq135
ros2 topic echo /gas/status
```

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
