# Go2机器人遥操作系统文档

## 概述

Kabutack_OS的遥操作系统是一个基于ZMQ（ZeroMQ）的分布式机器人遥控解决方案，支持Go2四足机器人的远程控制和状态监控。系统采用客户端-服务器架构，提供实时的运动控制、状态反馈和视觉数据传输功能。

## 系统架构

### 核心组件

1. **遥操作服务器 (TeleoperationServer)**
   - 运行在机器人端
   - 接收控制命令并转发给机器人
   - 发布机器人状态和传感器数据

2. **遥操作客户端 (TeleoperationClient)**
   - 运行在操作员端
   - 发送控制命令
   - 接收并显示机器人状态
   - 支持键盘控制和数据可视化

3. **硬件接口层**
   - 抽象的机器人接口 (RobotInterface)
   - Go2机器人具体实现 (Go2Robot)

### 通信协议

- **命令通道**: 使用ZMQ PUSH/PULL模式，端口5555
- **观测通道**: 使用ZMQ PUSH/PULL模式，端口5556
- **数据格式**: JSON序列化

## 快速开始

### 环境要求

```bash
pip install zmq numpy opencv-python rerun-sdk
# Go2机器人还需要安装unitree_sdk2py
```

### 启动服务器端（机器人端）

```bash
python -m app.teleoperation.teleoperation_host
```

### 启动客户端（操作员端）


```bash
python -m app.teleoperation.teleoperation_client
```