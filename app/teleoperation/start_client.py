"""
客户端侧，连接并控制机器人    
"""

from src.teleoperation.teleoperation_client import TeleoperationClient

if __name__ == '__main__':
    teleoperation_type = "keyboard"
    robot_ip = ""
    client = None

    try:
        client = TeleoperationClient(
            remote_robot_ip=robot_ip, 
            teleoperation_type=teleoperation_type
        )
        client.initialize()

    except KeyboardInterrupt:
        print("\nShutting down...")

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if client:
            client.disconnect() 