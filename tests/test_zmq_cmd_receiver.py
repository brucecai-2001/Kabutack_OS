import zmq
import json
import time

def cmd_receiver():
    """测试ZMQ客户端，接收teleoperation_client发送的命令"""
    # 创建上下文
    context = zmq.Context()
    
    # 创建PULL socket用于接收命令
    socket = context.socket(zmq.PULL)
    socket.setsockopt(zmq.CONFLATE, 1)  # 只保留最新消息
    
    # 连接到teleoperation_client的命令端口
    socket.connect("tcp://localhost:5555")
    print("命令接收器已启动，连接到tcp://localhost:5555")
    print("等待接收teleoperation_client发送的命令...")
    print("按Ctrl+C停止接收")
    
    try:
        while True:
            try:
                # 非阻塞接收消息
                json_msg = socket.recv_string(flags=zmq.NOBLOCK)
                
                # 解析JSON命令
                try:
                    cmd_data = json.loads(json_msg)
                    print(f"\n收到命令:")
                    print(f"  vx (前进速度): {cmd_data.get('vx', 0.0)} m/s")
                    print(f"  vy (侧向速度): {cmd_data.get('vy', 0.0)} m/s")
                    print(f"  vyaw (角速度): {cmd_data.get('vyaw', 0.0)} rad/s")
                    print(f"  时间戳: {cmd_data.get('timestamp', 'N/A')}")
                    print(f"  原始JSON: {json_msg}")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    print(f"原始消息: {json_msg}")
                    
            except zmq.Again:
                # 没有消息可接收，短暂等待
                time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\n接收器被用户中断")
    finally:
        # 关闭套接字和上下文
        socket.close()
        context.term()
        print("接收器已关闭")

if __name__ == "__main__":
    cmd_receiver()