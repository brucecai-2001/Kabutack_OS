import time
import cv2
import numpy as np
from typing import Dict, Any, Optional

# unitree sdk
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.go2.sport.sport_client import SportClient

from src.utils.image import encode_opencv_to_base64
from src.hardware_interface.base import RobotInterface

class Go2Robot(RobotInterface):
    def __init__(self) -> None:
        """初始化Go2机器人"""
        self._running = False
        self.observation: Optional[Dict[str, Any]] = None
        self.low_state: Optional[LowState_] = None
        
        # Unitree SDK 组件
        self.sport_client: Optional[SportClient] = None
        self.image_client: Optional[VideoClient] = None
        self.lowstate_subscriber: Optional[ChannelSubscriber] = None
        
        print("Go2Robot instance created. Call initialize() to start.")
    
    def initialize(self) -> None:
        """初始化机器人连接和SDK"""
        try:
            self._running = True
            
            # 初始化Unitree SDK
            ChannelFactoryInitialize(0, 'eth0')
            
            # 初始化SportClient, 控制高层运动
            self.sport_client = SportClient()
            self.sport_client.SetTimeout(10.0)
            self.sport_client.Init()
            
            # 初始化ImageClient，接收图像
            self.image_client = VideoClient()
            self.image_client.SetTimeout(3.0)
            self.image_client.Init()
            
            # 初始化底层状态订阅
            self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
            self.lowstate_subscriber.Init(self._low_state_message_handler, 10)
            
            self.sport_client.StandUp()
            print("Go2Robot initialized successfully.")
            
        except Exception as e:
            print(f"Failed to initialize Go2Robot: {e}")
            self.shutdown()
            raise
    
    def shutdown(self) -> None:
        """关闭机器人连接"""
        self._running = False
        
        # 清理资源
        if self.sport_client:
            try:
                # 停止机器人运动
                self.sport_client.Damp()
                time.sleep(5)
                self.sport_client.StandDown()
            except:
                pass
        
        print("Go2Robot shutdown completed.")
    
    def _low_state_message_handler(self, msg: LowState_) -> None:
        """底层状态消息回调处理器"""
        if not self._running:
            return
            
        try:
            # 更新状态
            self.low_state = msg
            
            # 获取当前图像
            front_image = self._capture_front_image()
            front_image_base64 = encode_opencv_to_base64(front_image) if front_image is not None else None
            
            # 构建observation
            self.observation = {
                "state": msg,
                "front_image": front_image_base64,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"处理状态消息时出错: {e}")
    
    def _capture_front_image(self) -> Optional[np.ndarray]:
        """从前置摄像头捕获图像"""
        if not self.image_client:
            return None
            
        try:
            # 从Go2机器人获取图像数据
            code, data = self.image_client.GetImageSample()
            if code != 0:
                print(f"获取图像样本错误. code:{code}")
                return None
            
            # 转换为numpy图像
            image_data = np.frombuffer(bytes(data), dtype=np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            
            return image
            
        except Exception as e:
            print(f"捕获图像时出错: {e}")
            return None
    
    def move(self, vx: float, vy: float, vyaw: float) -> None:
        """发送运动指令"""
        if not self._running or not self.sport_client:
            print("Robot not initialized or not running")
            return
            
        try:
            self.sport_client.Move(vx, vy, vyaw)
        except Exception as e:
            print(f"发送运动指令时出错: {e}")
    
    def get_observation(self) -> Dict[str, Any]:
        """获取观测数据"""
        if self.observation is None:
            return {
                "state": None,
                "front_image": None,
                "timestamp": time.time()
            }
        return self.observation.copy()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()