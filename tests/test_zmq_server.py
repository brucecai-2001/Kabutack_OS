import zmq
import time

def sender():
    # 创建上下文
    context = zmq.Context()
    
    # 创建一个PUSH类型的套接字（用于发送消息）
    socket = context.socket(zmq.PUSH)
    
    # 绑定到指定地址
    socket.bind("tcp://*:5555")
    print("发送者已启动，绑定到tcp://*:5555")
    
    try:
        # 发送5条消息
        for i in range(5):
            message = f"这是第 {i+1} 条消息"
            socket.send_string(message)
            print(f"已发送: {message}")
            time.sleep(1)  # 暂停1秒
    except KeyboardInterrupt:
        print("\n发送者被用户中断")
    finally:
        # 关闭套接字和上下文
        socket.close()
        context.term()

if __name__ == "__main__":
    sender()