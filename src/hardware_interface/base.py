from abc import ABC, abstractmethod
from typing import Dict, Any

class RobotInterface(ABC):
    """机器人接口基类"""
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化机器人连接"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭机器人连接"""
        pass
    
    @abstractmethod
    def get_observation(self) -> Dict[str, Any]:
        """获取观测数据"""
        pass
    
    @abstractmethod
    def move(self, vx: float, vy: float, vyaw: float) -> None:
        """发送运动指令"""
        pass