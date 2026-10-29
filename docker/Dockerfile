# ROS 2 Humble + デスクトップ(noVNC) + Gazebo Fortress (Ignition) + ros_gz
# Mac/Windows でも、ブラウザ(http://localhost:6080)でGazeboのGUIを表示できる構成。
FROM tiryoh/ros2-desktop-vnc:humble

ENV DEBIAN_FRONTEND=noninteractive

# Gazebo Fortress 本体と ROS 2 <-> Gazebo ブリッジ (ros_gz)
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget gnupg lsb-release \
    && wget -qO - https://packages.osrfoundation.org/gazebo.gpg \
        | gpg --dearmor -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        ignition-fortress \
        ros-humble-ros-gz \
        python3-colcon-common-extensions \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# ソフトウェアレンダリング(GPUなしのDocker向け)
ENV LIBGL_ALWAYS_SOFTWARE=1 \
    QT_X11_NO_MITSHM=1

WORKDIR /home/ubuntu/ros2_ws
