"""
Unitree Go2 Client based on ZMQ
"""
import zmq
import json
import time
import argparse

class Go2Client:
    def __init__(self, zmq_address):
        """初始化ZMQ客户端"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(zmq_address)
        print(f"已连接到ZMQ服务器: {zmq_address}")
        
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
            self.socket.send_string(json_command)
            print(f"已发送移动指令: vx={vx}, vy={vy}, vyaw={vyaw}")
            return True
        except Exception as e:
            print(f"发送指令时出错: {e}")
            return False
    
    def close(self):
        """关闭ZMQ连接"""
        self.socket.close()
        self.context.term()
        print("ZMQ连接已关闭")

# def main():
#     # 解析命令行参数
#     parser = argparse.ArgumentParser(description='向SportNode发送移动指令的ZMQ客户端')
#     parser.add_argument('--address', type=str, default="tcp://127.0.0.1:5555",
#                       help='ZMQ服务器地址 (默认: tcp://127.0.0.1:5555)')
#     args = parser.parse_args()
    
#     # 创建客户端实例
#     client = Go2Client(args.address)
    
#     try:
#         # 示例: 发送一系列移动指令
#         print("发送前进指令 (vx=0.2)...")
#         client.send_move_command(vx=0.2)
#         time.sleep(2)  # 前进2秒
        
#         print("发送右转指令 (vyaw=0.1)...")
#         client.send_move_command(vyaw=0.1)
#         time.sleep(2)  # 右转2秒
        
#         print("发送向左移动指令 (vy=0.1)...")
#         client.send_move_command(vy=0.1)
#         time.sleep(2)  # 向左移动2秒
        
#         print("发送停止指令...")
#         client.send_move_command()  # 所有参数默认为0，即停止
#         time.sleep(1)
        
#     except KeyboardInterrupt:
#         print("\n用户中断，发送停止指令...")
#         client.send_move_command()  # 停止机器人
#     finally:
#         client.close()

# if __name__ == "__main__":
#     main()
