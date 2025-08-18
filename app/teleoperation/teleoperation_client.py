import zmq
import json
import time
import threading
import numpy as np
from typing import Dict, Any, Optional, Callable

from src.utils.image import decode_image_from_b64

class TeleoperationClient:
    """遥操作客户端，支持基础遥操作和键盘控制功能"""

    def __init__(self, remote_robot_ip: str = "localhost", cmd_port: int = 5555, obs_port: int = 5556,
                 enable_keyboard_control: bool = False, max_linear_speed: float = 1.0, max_angular_speed: float = 1.0):
        """
        初始化遥操作客户端
        
        Args:
            remote_robot_ip: 服务器地址
            cmd_port: 命令端口
            obs_port: 观测数据端口
            enable_keyboard_control: 是否启用键盘控制功能
            max_linear_speed: 最大线性速度 (仅在启用键盘控制时使用)
            max_angular_speed: 最大角速度 (仅在启用键盘控制时使用)
        """
        self.server_address = remote_robot_ip
        self.cmd_port = cmd_port
        self.obs_port = obs_port
        self.enable_keyboard_control = enable_keyboard_control
        
        # ZMQ设置
        self.cmd_context = zmq.Context()
        self.cmd_socket = self.cmd_context.socket(zmq.PUSH)
        
        self.obs_context = zmq.Context()
        self.obs_socket = self.obs_context.socket(zmq.PULL)
        
        # 数据缓存
        self._latest_observation = None
        self._latest_state = None
        self._latest_image = None
        self._lock = threading.Lock()
        
        # 运行状态
        self._running = False
        self._obs_thread = None
        
        # 回调函数
        self._observation_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # 键盘控制相关属性（仅在启用时使用）
        if self.enable_keyboard_control:
            self.max_linear_speed = max_linear_speed
            self.max_angular_speed = max_angular_speed
            
            # 当前速度
            self.current_vx = 0.0
            self.current_vy = 0.0
            self.current_vyaw = 0.0
            
            # 控制线程
            self._control_thread = None
            self._control_running = False
        
    def connect(self):
        """连接到遥操作服务器"""
        try:
            # 连接命令socket
            self.cmd_socket.connect(f"tcp://*:{self.cmd_port}")
            
            # 连接观测socket
            self.obs_socket.connect(f"tcp://{self.server_address}:{self.obs_port}")
            
            # 启动观测数据接收线程
            self._running = True
            self._obs_thread = threading.Thread(target=self._obs_receive_loop, daemon=True)
            self._obs_thread.start()
            
            print(f"Connected to teleoperation server at {self.server_address}")
            
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            raise
    
    def disconnect(self):
        """断开与服务器的连接"""
        # 如果启用了键盘控制，先停止键盘控制
        if self.enable_keyboard_control:
            self.stop_keyboard_control()
            
        self._running = False
        
        if self._obs_thread and self._obs_thread.is_alive():
            self._obs_thread.join(timeout=2.0)
        
        self.cmd_socket.close()
        self.obs_socket.close()
        self.cmd_context.term()
        self.obs_context.term()
        
        print("Disconnected from teleoperation server")
    
    def _obs_receive_loop(self):
        """观测数据接收循环"""
        while self._running:
            try:
                # 接收观测数据
                json_msg = self.obs_socket.recv_string(flags=zmq.NOBLOCK)
                observation = json.loads(json_msg)
                
                with self._lock:
                    self._latest_observation = observation
                    
                    # 解析状态数据
                    if 'state' in observation and observation['state']:
                        self._latest_state = observation['state']
                    
                    # 解析图像数据
                    if 'front_image' in observation and observation['front_image']:
                        try:
                            image = decode_image_from_b64(observation['front_image'])
                            if image is not None:
                                self._latest_image = image
                        except Exception as e:
                            print(f"Failed to decode image: {e}")
                
                # 调用回调函数
                if self._observation_callback:
                    self._observation_callback(observation)
                    
            except zmq.Again:
                # 没有消息可接收
                time.sleep(0.01)
            except Exception as e:
                print(f"Observation receive error: {e}")
                time.sleep(0.1)
    
    def send_move_command(self, vx: float, vy: float, vyaw: float):
        """
        发送运动命令
        
        Args:
            vx: 前进速度 (m/s)
            vy: 侧向速度 (m/s)
            vyaw: 角速度 (rad/s)
        """
        try:
            cmd_data = {
                'vx': float(vx),
                'vy': float(vy),
                'vyaw': float(vyaw),
                'timestamp': time.time()
            }
            
            json_msg = json.dumps(cmd_data)
            self.cmd_socket.send_string(json_msg, flags=zmq.NOBLOCK)
            
        except Exception as e:
            print(f"Failed to send move command: {e}")
    
    def get_latest_observation(self) -> Optional[Dict[str, Any]]:
        """获取最新的完整观测数据"""
        with self._lock:
            return self._latest_observation.copy() if self._latest_observation else None
    
    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        """获取最新的状态数据"""
        with self._lock:
            return self._latest_state.copy() if self._latest_state else None
    
    def get_latest_image(self) -> Optional[np.ndarray]:
        """获取最新的图像数据"""
        with self._lock:
            return self._latest_image.copy() if self._latest_image is not None else None
    
    def set_observation_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置观测数据回调函数"""
        self._observation_callback = callback
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._running
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
    
    # 键盘控制相关方法（仅在启用键盘控制时可用）
    def start_keyboard_control(self):
        """启动键盘控制"""
        if not self.enable_keyboard_control:
            raise RuntimeError("Keyboard control is not enabled. Set enable_keyboard_control=True when creating the client.")
            
        if not self.is_connected():
            raise RuntimeError("Client not connected. Call connect() first.")
        
        self._control_running = True
        self._control_thread = threading.Thread(target=self._keyboard_control_loop, daemon=True)
        self._control_thread.start()
        
        print("Keyboard control started. Use WASD keys to control the robot.")
        print("W/S: Forward/Backward, A/D: Left/Right, Q/E: Turn Left/Right, Space: Stop, ESC: Quit")
    
    def stop_keyboard_control(self):
        """停止键盘控制"""
        if not self.enable_keyboard_control:
            return
            
        self._control_running = False
        if self._control_thread and self._control_thread.is_alive():
            self._control_thread.join(timeout=1.0)
    
    def _keyboard_control_loop(self):
        """键盘控制循环"""
        try:
            import keyboard
        except ImportError:
            print("Please install keyboard library: pip install keyboard")
            return
        
        while self._control_running:
            try:
                # 重置速度
                vx, vy, vyaw = 0.0, 0.0, 0.0
                
                # 检查按键状态
                if keyboard.is_pressed('w'):
                    vx = self.max_linear_speed
                elif keyboard.is_pressed('s'):
                    vx = -self.max_linear_speed
                
                if keyboard.is_pressed('a'):
                    vy = self.max_linear_speed
                elif keyboard.is_pressed('d'):
                    vy = -self.max_linear_speed
                
                if keyboard.is_pressed('q'):
                    vyaw = self.max_angular_speed
                elif keyboard.is_pressed('e'):
                    vyaw = -self.max_angular_speed
                
                if keyboard.is_pressed('space'):
                    vx = vy = vyaw = 0.0
                
                if keyboard.is_pressed('esc'):
                    break
                
                # 发送命令
                self.send_move_command(vx, vy, vyaw)
                
                time.sleep(0.1)  # 10Hz控制频率
                
            except Exception as e:
                print(f"Keyboard control error: {e}")
                time.sleep(0.1)
        
        # 停止机器人
        self.send_move_command(0.0, 0.0, 0.0)
        print("Keyboard control stopped")


if __name__ == "__main__":
    
    remote_robot_ip = "192.168.31.86"
    try:
        # 创建启用键盘控制的遥操作客户端
        with TeleoperationClient(remote_robot_ip, enable_keyboard_control=True) as client:
            client.connect()
            
            # 设置观测数据回调
            def on_observation(obs):
                if 'timestamp' in obs:
                    print(f"Received observation at {obs['timestamp']}")
            
            client.set_observation_callback(on_observation)
            
            # 启动键盘控制
            client.start_keyboard_control()
            
            # 保持运行
            try:
                while client.is_connected():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                
    except Exception as e:
        print(f"Error: {e}")