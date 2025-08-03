"""
Unitree Go2 Client based on ZMQ
"""
import zmq
import json
import time
import threading

from src.utils.image import decode_image_from_b64

class DeviceNotConnectedError(Exception):
    """设备未连接异常"""
    pass

class Go2ROS2Client:
    def __init__(self, 
                 go2_address: str, 
                 command_port: int, 
                 state_port: int, 
                 img_port: int, 
                 connect_timeout_s: float = 100.0):   
        """
        初始化Go2ROS2Client
        :param go2_address: Go2的IP地址
        :param command_port: 命令端口
        :param state_port: 状态端口
        :param img_port: 图像端口
        :param connect_timeout_s: 连接超时时间（秒）
        """
        self.go2_address = go2_address
        self.command_port = command_port
        self.state_port = state_port
        self.img_port = img_port
        self.connect_timeout_s = connect_timeout_s

        self.running = False
        self.latest_state = None
        self.latest_image = None

        """初始化ZMQ客户端"""
        self.context = zmq.Context()

        # 发送命令的socket
        self.command_socket = self.context.socket(zmq.PUSH)
        self.command_socket.bind(f"tcp://*:{command_port}")
        self.command_socket.setsockopt(zmq.CONFLATE, 1)
        print(f"创建命令ZMQ服务器: tcp://192.168.31.158:{command_port}")
    
        # 接收状态的socket
        self.state_socket = self.context.socket(zmq.PULL)
        self.state_socket.connect(f"tcp://{go2_address}:{state_port}")
        self.state_socket.setsockopt(zmq.CONFLATE, 1)  # 订阅所有消息
        print(f"连接到状态ZMQ服务器: tcp://{go2_address}:{state_port}")
        
        # 接收图像的socket
        self.image_socket = self.context.socket(zmq.PULL)
        self.image_socket.connect(f"tcp://{go2_address}:{img_port}")
        self.image_socket.setsockopt(zmq.CONFLATE, 1)  # 只保留最新的图像
        print(f"连接到图像ZMQ服务器: tcp://{go2_address}:{img_port}")
        
        # 创建poller用于同时监听多个socket
        self.poller = zmq.Poller()
        self.poller.register(self.state_socket, zmq.POLLIN)
        self.poller.register(self.image_socket, zmq.POLLIN)
            
        # 启动统一的接收线程
        self.running = True
        self.receiver_thread = threading.Thread(target=self._receiver_loop)
        self.receiver_thread.daemon = True
        self.receiver_thread.start()
        
        # 短暂延迟确保连接建立
        time.sleep(0.1)

    def send_move_command(self, vx=0.0, vy=0.0, vyaw=0.0):
        """发送移动指令到服务器"""
        # 创建包含移动参数的字典
        command = {
            'vx': vx,    # x方向速度
            'vy': vy,    # y方向速度
            'vyaw': vyaw # 偏航角速度
        }
        
        # 转换为JSON字符串并发送
        try:
            json_command = json.dumps(command)
            self.command_socket.send_string(json_command)
            print(f"已发送移动指令: vx={vx}, vy={vy}, vyaw={vyaw}")
            return True
        except Exception as e:
            print(f"发送指令时出错: {e}")
            return False
    
    def _receiver_loop(self):
        """统一的接收循环（在后台线程中运行）"""
        while self.running:
            try:
                # 使用poller同时监听状态和图像socket，超时时间100ms
                socks = dict(self.poller.poll(100))
                
                # 检查状态socket是否有数据
                if self.state_socket in socks:
                    try:
                        state_json = self.state_socket.recv_string(zmq.NOBLOCK)
                        self.latest_state = json.loads(state_json)
                    except zmq.Again:
                        pass
                    except Exception as e:
                        print(f"接收状态数据时出错: {e}")
                
                # 检查图像socket是否有数据
                if self.image_socket in socks:
                    try:
                        image_data = self.image_socket.recv_string(zmq.NOBLOCK)
                        self.latest_image = decode_image_from_b64(image_data)
                    except zmq.Again:
                        pass
                    except Exception as e:
                        print(f"接收图像数据时出错: {e}")
                        
            except Exception as e:
                print(f"接收数据时出错: {e}")
                time.sleep(0.1)
    
    def get_latest_state(self):
        """获取最新的状态数据"""
        return self.latest_state
    
    def get_latest_image(self):
        """获取最新的图像数据"""
        return self.latest_image

    def close(self):
        """关闭ZMQ连接"""
        # 停止接收线程
        if hasattr(self, 'receiver_thread') and self.receiver_thread:
            self.running = False
            self.receiver_thread.join(timeout=1.0)
        
        # 关闭sockets
        self.command_socket.close()
        self.state_socket.close()
        self.image_socket.close()
        
        self.context.term()
        print("ZMQ连接已关闭")