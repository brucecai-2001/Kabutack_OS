import zmq
import json
import time
import threading

from src.hardware_interface.base import RobotInterface

class TeleoperationServer:
    def __init__(self, robot: RobotInterface, client_ip: str, cmd_port=5555, obs_port=5556):
        self.robot = robot
        self.running = True
        self.cmd_port = cmd_port
        self.obs_port = obs_port
        
        # ZMQ设置
        self.cmd_context = zmq.Context()
        self.cmd_socket = self.cmd_context.socket(zmq.PULL)
        self.cmd_socket.connect(f"tcp://{client_ip}:{cmd_port}")
        
        self.obs_context = zmq.Context()
        self.obs_socket = self.obs_context.socket(zmq.PUSH)
        self.obs_socket.bind(f"tcp://*:{obs_port}")
    
    def start(self):
        # 启动命令监听线程
        cmd_thread = threading.Thread(target=self._cmd_listen_loop, daemon=True)
        cmd_thread.start()
        
        # 启动观测发布线程
        obs_thread = threading.Thread(target=self._obs_publish_loop, daemon=True)
        obs_thread.start()
        
        print(f"Teleoperation server started on ports {self.cmd_port}(cmd) and {self.obs_port}(obs)")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _cmd_listen_loop(self):
        while self.running:
            try:
                json_msg = self.cmd_socket.recv_string(flags=zmq.NOBLOCK)
                cmd_data = json.loads(json_msg)
                
                vx = float(cmd_data.get('vx', 0.0))
                vy = float(cmd_data.get('vy', 0.0))
                vyaw = float(cmd_data.get('vyaw', 0.0))
                
                self.robot.move(vx, vy, vyaw)
                
            except zmq.Again:
                pass
            except Exception as e:
                print(f"Command processing error: {e}")
    
    def _obs_publish_loop(self):
        while self.running:
            try:
                observation = self.robot.get_observation()
                json_msg = json.dumps(observation, default=str)  # 添加default=str处理序列化
                self.obs_socket.send_string(json_msg, flags=zmq.NOBLOCK)
                time.sleep(0.1)  # 10Hz发布频率
            except Exception as e:
                print(f"Observation publishing error: {e}")
    
    def stop(self):
        self.running = False
        self.cmd_socket.close()
        self.obs_socket.close()
        self.cmd_context.term()
        self.obs_context.term()

def load_robot(robot_type: str):
    """动态加载机器人实例"""
    if robot_type == "go2":
        from src.hardware_interface.go2 import Go2Robot
        robot = Go2Robot()
        robot.initialize()  # 显式初始化
        return robot
    elif robot_type == "xlerobot":
        raise NotImplementedError("Hold on, xlerobot is on the way")
    else:
        raise ValueError(f"Unknown robot type: {robot_type}")

if __name__ == "__main__":
    
    robot_type = "go2"
    robot = None
    
    try:
        robot = load_robot(robot_type)
        server = TeleoperationServer(robot, "192.168.31.156")
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if robot:
            robot.shutdown()