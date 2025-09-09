import sys
import tty
import termios
import select
import threading
import time
from teleoperation.teleoperation_client import TeleoperationClient

class KeyboardTeleoperationClient(TeleoperationClient):
    """支持键盘控制的遥操作客户端"""
    
    def __init__(self, remote_robot_ip: str = "localhost",
                       cmd_port: int = 5555, 
                       obs_port: int = 5556,
                       max_linear_speed: float = 0.5, 
                       max_angular_speed: float = 0.5,
                       enable_rerun_logging: bool = True
        ):
        """
        初始化键盘控制遥操作客户端
        
        Args:
            remote_robot_ip: 服务器地址
            cmd_port: 命令端口
            obs_port: 观测数据端口
            max_linear_speed: 最大线性速度
            max_angular_speed: 最大角速度
            enable_rerun_logging: 是否启用rerun数据记录
        """
        # 调用父类初始化
        super().__init__(remote_robot_ip, cmd_port, obs_port, enable_rerun_logging)
        
        # 键盘控制相关属性
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed
        
        # 当前速度
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_vyaw = 0.0
        
        # 控制线程
        self._control_thread = None
        self._control_running = True
        
        # 启动键盘控制
        self._start_keyboard_control()
    
    def _start_keyboard_control(self):
        """启动键盘控制功能"""
        self._control_thread = threading.Thread(target=self._keyboard_control_loop, daemon=True)
        self._control_thread.start()
        
        # 打印控制说明
        print("Keyboard control started. Use WASD keys to control the robot.")
        print("W/S: Forward/Backward, A/D: Left/Right, Q/E: Turn Left/Right, Space: Stop, ESC: Quit")
    
    def disconnect(self):
        """断开连接，包括停止键盘控制"""
        # 停止键盘控制
        self._control_running = False
        if self._control_thread and self._control_thread.is_alive():
            self._control_thread.join(timeout=1.0)
        
        # 调用父类的断开连接方法
        super().disconnect()
    
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
                        self.send_move_command(0.0, 0.0, 0.0)
                        pressed_keys.clear()
                        continue
                    elif key.lower() in 'wasdqe':
                        pressed_keys.add(key.lower())
                
                # 计算当前速度
                vx, vy, vyaw = self._calculate_velocities(pressed_keys)
                
                # 发送命令
                self.send_move_command(vx, vy, vyaw)
                
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
    
    def _calculate_velocities(self, pressed_keys: set) -> tuple:
        """根据按键状态计算速度"""
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
        
        return vx, vy, vyaw