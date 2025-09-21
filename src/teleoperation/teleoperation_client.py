import sys
import zmq
import json
import time
import threading
import tty
import select
import termios
import rerun as rr
from typing import Dict, Any
from src.utils.image import decode_image_from_b64

class TeleoperationClient:
    """遥操作客户端基础类，提供核心的通信和数据处理功能"""

    def __init__(self, remote_robot_ip: str = "localhost",
                       cmd_port: int = 5555, 
                       obs_port: int = 5556,
                       enable_rerun_logging: bool = True,
                       teleoperation_type: str = "keyboard"
        ):
        """
        初始化遥操作客户端基础功能
        
        Args:
            remote_robot_ip: 服务器地址
            cmd_port: 命令端口
            obs_port: 观测数据端口
            enable_rerun_logging: 是否启用rerun数据记录
        """
        self.server_address = remote_robot_ip
        self.cmd_port = cmd_port
        self.obs_port = obs_port
        self.enable_rerun_logging = enable_rerun_logging
        
        # ZMQ设置
        self.context = zmq.Context()

        # 发送命令socket
        self.cmd_socket = self.context.socket(zmq.PUSH)
        self.cmd_socket.setsockopt(zmq.CONFLATE, 1)
        self.cmd_socket.bind(f"tcp://*:{self.cmd_port}")
        
        # 接收观测socket
        self.obs_socket = self.context.socket(zmq.PULL)
        self.obs_socket.setsockopt(zmq.CONFLATE, 1)
        self.obs_socket.connect(f"tcp://{self.server_address}:{self.obs_port}")
        
        # 数据缓存
        self._latest_observation = None
        self._latest_state = None
        self._latest_image = None
        self._lock = threading.Lock()
        
        # 运行状态
        self._running = True
        self._obs_thread = None

        # 控制线程
        self._control_thread = None
        self._control_running = True
        self.teleoperation_type = teleoperation_type
        self.max_linear_speed = 0.5
        self.max_angular_speed = 0.5
    
    def initialize(self):
        """初始化连接和控制线程"""
        try:
            # 初始化rerun日志
            if self.enable_rerun_logging:
                rr.init("teleoperation_client", spawn=True)
                rr.log("description", rr.TextDocument("Teleoperation Client Data Visualization", 
                                                     media_type=rr.MediaType.MARKDOWN))
            
            # 启动观测数据接收线程
            self._obs_thread = threading.Thread(target=self._obs_receive_loop, daemon=True)
            self._obs_thread.start()
            
            # 根据遥操作类型启动相应的控制线程
            if self.teleoperation_type == "keyboard":
                self._control_thread = threading.Thread(target=self._keyboard_control_loop, daemon=True)
                print("使用键盘控制模式")
            elif self.teleoperation_type == "gamepad":
                raise NotImplementedError("not implemented")
            else:
                raise ValueError(f"不支持的遥操作类型: {self.teleoperation_type}")
            
            self._control_thread.start()
            print(f"已连接到机器人服务器: {self.server_address}")
            
        except Exception as e:
            print(f"初始化失败: {e}")
            self.disconnect()
            raise
    
    def disconnect(self):
        """断开与服务器的连接"""
        self._running = False
        self._control_running = False
        
        if self._control_thread and self._control_thread.is_alive():
            self._control_thread.join(timeout=1.0)
        
        if self._obs_thread and self._obs_thread.is_alive():
            self._obs_thread.join(timeout=2.0)
        
        # 关闭socket
        self.cmd_socket.close()
        self.obs_socket.close()
        self.context.term()
        
        print("Disconnected from teleoperation server")
    
    def _log_state_to_rerun(self, state_data: Dict[str, Any]):
        """将状态数据记录到rerun"""
        if not self.enable_rerun_logging or not state_data:
            return
            
        try:
            # 记录位置信息
            if 'position' in state_data:
                pos = state_data['position']
                if isinstance(pos, (list, tuple)) and len(pos) >= 3:
                    rr.log("robot/position", rr.Points3D([pos[:3]], colors=[0, 255, 0]))

        except Exception as e:
            print(f"Failed to log state to rerun: {e}")
    
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
                        # 记录状态数据到rerun
                        if self.enable_rerun_logging:
                            self._log_state_to_rerun(observation['state'])
                    
                    # 解析图像数据
                    if 'front_image' in observation and observation['front_image']:
                        try:
                            image = decode_image_from_b64(observation['front_image'])
                            if image is not None:
                                self._latest_image = image
                                # 记录图像数据到rerun
                                if self.enable_rerun_logging:
                                    rr.log("camera/front_image", rr.Image(image))
                        except Exception as e:
                            print(f"Failed to decode image: {e}")
                    
            except zmq.Again:
                # 没有消息可接收
                time.sleep(0.01)
            except Exception as e:
                print(f"Observation receive error: {e}")
                time.sleep(0.1)
    
    def _send_move_command(self, vx: float, vy: float, vyaw: float):
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
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._running
    
    def get_latest_observation(self) -> Dict[str, Any]:
        """获取最新的观测数据"""
        with self._lock:
            return self._latest_observation
    
    def get_latest_state(self) -> Dict[str, Any]:
        """获取最新的状态数据"""
        with self._lock:
            return self._latest_state
    
    def get_latest_image(self):
        """获取最新的图像数据"""
        with self._lock:
            return self._latest_image

    def _keyboard_control_loop(self):
        """键盘控制循环 - 使用termios实现"""
        # 保存原始终端设置
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            # 设置终端为原始模式
            tty.setraw(sys.stdin.fileno())
            
            print("Keyboard control active. Press keys to control:")
            print("W/S: Forward/Backward, A/D: Left/Right, Q/E: Turn Left/Right, Space: Stop, ESC: Quit")
            print("Press and hold keys for continuous movement...")
            
            # 按键状态跟踪
            pressed_keys = set()
            
            while self._control_running:
                # 检查是否有输入可用
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    key = sys.stdin.read(1)
                    
                    # 处理特殊键
                    if ord(key) == 27:  # ESC键
                        break
                    elif ord(key) == 32:  # 空格键
                        # 立即停止
                        self._send_move_command(0.0, 0.0, 0.0)
                        pressed_keys.clear()
                        continue
                    elif key.lower() in 'wasdqe':
                        pressed_keys.add(key.lower())
                
                # 计算当前速度
                vx = 0.0
                vy = 0.0
                vyaw = 0.0

                if 'w' in pressed_keys:
                    vx = self.max_linear_speed
                elif 's' in pressed_keys:
                    vx = -self.max_linear_speed
                
                if 'a' in pressed_keys:
                    vy = self.max_linear_speed
                elif 'd' in pressed_keys:
                    vy = -self.max_linear_speed
                
                if 'q' in pressed_keys:
                    vyaw = self.max_angular_speed
                elif 'e' in pressed_keys:
                    vyaw = -self.max_angular_speed

                # 发送命令
                self._send_move_command(vx, vy, vyaw)
                
                # 清除按键状态（因为termios不能持续检测按键状态）
                pressed_keys.clear()
                
                # 控制循环频率
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nKeyboard control interrupted")

        finally:
            # 恢复原始终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            print("\nKeyboard control stopped") 