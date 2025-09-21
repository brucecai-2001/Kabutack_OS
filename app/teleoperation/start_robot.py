"""
机器人侧，启动机器人    
"""

from src.teleoperation.teleoperation_host import TeleoperationServer, load_robot

if __name__ == "__main__":
    
    robot_type = "go2"
    client_ip = "192.168.31.158"
    robot = None

    try:

        robot = load_robot(robot_type)
        server = TeleoperationServer(robot, client_ip)
        server.start()

    except KeyboardInterrupt:
        print("\nShutting down...")

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if robot:
            robot.shutdown()