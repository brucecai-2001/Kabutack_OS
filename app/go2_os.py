import sys
import os
import time
import threading
import select
import termios
import tty

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.hardware_interface.go2 import Go2ROS2Client

def get_key():
    """获取键盘输入（非阻塞）"""
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None

def keyboard_control_thread(client: Go2ROS2Client):
    """键盘控制线程"""
    # 保存原始终端设置
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        # 设置终端为原始模式
        tty.setraw(sys.stdin.fileno())

        while True:
            key = get_key()
            if key:
                key = key.lower()
                
                if key == 'w':
                    client.send_move_command(vx=0.5, vy=0.0, vyaw=0.0)
                    print("前进")
                elif key == 's':
                    client.send_move_command(vx=-0.5, vy=0.0, vyaw=0.0)
                    print("后退")
                elif key == 'a':
                    client.send_move_command(vx=0.0, vy=0.0, vyaw=0.5)
                    print("左转")
                elif key == 'd':
                    client.send_move_command(vx=0.0, vy=0.0, vyaw=-0.5)
                    print("右转")
                elif key == ' ':
                    client.send_move_command(vx=0.0, vy=0.0, vyaw=0.0)
                    print("停止")
                elif key == 'q':
                    print("退出控制")
                    break
            
            time.sleep(0.1)
    
    finally:
        # 恢复终端设置
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def print_state_thread(client: Go2ROS2Client):
    """打印状态数据线程"""
    while True:
        state = client.get_latest_state()
        if state:
            print(f"状态数据: {state}")
        time.sleep(1.0)  # 每秒打印一次状态

if __name__ == '__main__':
    # 初始化客户端，需要提供Go2的IP地址和端口
    # 这里使用默认值，你可能需要根据实际情况修改
    go2_address = "192.168.31.86"  # Go2的IP地址
    command_port = 5555  # 命令端口
    state_port = 5557    # 状态端口
    img_port = 5556      # 图像端口
    
    try:
        print(f"连接到Go2机器人: {go2_address}")
        client = Go2ROS2Client(go2_address, command_port, state_port, img_port)
        
        # 启动状态打印线程
        state_thread = threading.Thread(target=print_state_thread, args=(client,))
        state_thread.daemon = True
        state_thread.start()
        
        # 启动键盘控制（主线程）
        print("\n键盘控制说明: \nW - 前进\nS - 后退\nA - 左转\nD - 右转\n空格 - 停止\nQ - 退出\n开始控制...\n")
        keyboard_control_thread(client)
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        if 'client' in locals():
            client.close()
        print("程序已退出")
    