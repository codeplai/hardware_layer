FROM ros:foxy-ros-base

# Instalar colcon para compilar mensajes custom
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-colcon-common-extensions && \
    rm -rf /var/lib/apt/lists/*

# Copiar paquete de mensajes y compilar
COPY minebot_msgs /ros2_ws/src/minebot_msgs
RUN /bin/bash -c "source /opt/ros/foxy/setup.bash && \
    cd /ros2_ws && \
    colcon build --packages-select minebot_msgs"

# Copiar nodo y config
COPY nodes /ros2_ws/src/hardware_layer/nodes
COPY config /ros2_ws/src/hardware_layer/config

# Variables de entorno ROS2 / DDS
ENV ROS_DOMAIN_ID=42
ENV ROS_LOCALHOST_ONLY=0
ENV ROS_IP=10.95.229.127
ENV ROS_HOSTNAME=10.95.229.127
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Entrypoint: configurar serial, source ROS2 + workspace, lanzar nodo
CMD ["/bin/bash", "-c", \
    "stty -F /dev/ttyHS1 115200 raw -echo && \
     source /opt/ros/foxy/setup.bash && \
     source /ros2_ws/install/setup.bash && \
     python3 /ros2_ws/src/hardware_layer/nodes/gas_sensor_node.py"]
