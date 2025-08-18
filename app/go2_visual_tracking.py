import sys
import os
import cv2
import numpy as np
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.hardware_interface.go2 import Go2ROS2Client
from src.core_modules.visual.yolo.yolo import YoloMultiTask
from src.core_modules.controller.pid import PIDController

# 配置参数
GO2_ADDRESS = "192.168.31.86"
COMMAND_PORT = 5555
STATE_PORT = 5557
IMG_PORT = 5556
YOLO_MODEL_PATH = "yolo11n.pt"
TARGET_CLASS = "person"

# 跟踪参数
TARGET_CENTER_X = 320  # 图像中心X坐标（假设640x480分辨率）
TARGET_CENTER_Y = 240  # 图像中心Y坐标
TARGET_BOX_AREA = 50000  # 目标框的理想面积
DETECTION_TIMEOUT = 2.0  # 检测超时时间（秒）

# 全局变量
tracking = False
last_detection_time = 0

def detect_target(detector, image, target_class):
    """
    检测目标对象
    
    Args:
        detector: YOLO检测器
        image: 输入图像
        target_class: 目标类别
        
    Returns:
        target_box: 目标边界框 [x1, y1, x2, y2]，如果未检测到则返回None
    """
    try:
        # 使用YOLO进行检测
        results = detector(image)
        
        if "boxes_xyxy" not in results or len(results["boxes_xyxy"]) == 0:
            return None
        
        # 查找目标类别
        target_boxes = []
        for i, name in enumerate(results["names"]):
            if name == target_class:
                box = results["boxes_xyxy"][i].cpu().numpy()
                conf = results["confidence"][i].cpu().numpy()
                target_boxes.append((box, conf))
        
        if not target_boxes:
            return None
        
        # 选择置信度最高的目标
        best_box = max(target_boxes, key=lambda x: x[1])[0]
        return best_box
        
    except Exception as e:
        print(f"目标检测错误: {e}")
        return None

def calculate_control_commands(target_box, image_shape, pid_x, pid_y, pid_yaw):
    """
    根据目标位置计算控制命令
    
    Args:
        target_box: 目标边界框 [x1, y1, x2, y2]
        image_shape: 图像尺寸 (height, width)
        pid_x, pid_y, pid_yaw: PID控制器
        
    Returns:
        vx, vy, vyaw: 控制命令
    """
    h, w = image_shape[:2]
    
    # 计算目标中心点
    center_x = (target_box[0] + target_box[2]) / 2
    center_y = (target_box[1] + target_box[3]) / 2
    
    # 计算目标框面积
    box_area = (target_box[2] - target_box[0]) * (target_box[3] - target_box[1])
    
    # 计算误差
    error_x = center_x - w / 2  # X轴误差（像素）
    error_y = h / 2 - center_y  # Y轴误差（像素，注意图像坐标系）
    error_area = TARGET_BOX_AREA - box_area  # 面积误差
    
    # 归一化误差
    error_x_norm = error_x / (w / 2)  # 归一化到[-1, 1]
    error_y_norm = error_y / (h / 2)  # 归一化到[-1, 1]
    error_area_norm = error_area / TARGET_BOX_AREA  # 归一化面积误差
    
    # 使用PID控制器计算控制命令
    vyaw = -pid_yaw.update(error_x_norm)  # 偏航控制（左右旋转）
    vx = pid_y.update(error_area_norm)    # 前后移动控制
    vy = -pid_x.update(error_y_norm)      # 左右移动控制
    
    return vx, vy, vyaw

def draw_tracking_info(image, target_box=None, tracking_status=False):
    """
    在图像上绘制跟踪信息
    
    Args:
        image: 输入图像
        target_box: 目标边界框
        tracking_status: 跟踪状态
        
    Returns:
        annotated_image: 标注后的图像
    """
    annotated = image.copy()
    h, w = image.shape[:2]
    
    # 绘制图像中心十字线
    cv2.line(annotated, (w//2-20, h//2), (w//2+20, h//2), (0, 255, 0), 2)
    cv2.line(annotated, (w//2, h//2-20), (w//2, h//2+20), (0, 255, 0), 2)
    
    # 绘制目标框
    if target_box is not None:
        x1, y1, x2, y2 = target_box.astype(int)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
        
        # 绘制目标中心点
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        cv2.circle(annotated, (center_x, center_y), 5, (0, 0, 255), -1)
        
        # 绘制连接线
        cv2.line(annotated, (w//2, h//2), (center_x, center_y), (255, 0, 0), 2)
        
        # 显示目标信息
        cv2.putText(annotated, f"Target: {TARGET_CLASS}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # 显示跟踪状态
    status = "TRACKING" if tracking_status else "SEARCHING"
    color = (0, 255, 0) if tracking_status else (0, 0, 255)
    cv2.putText(annotated, f"Status: {status}", (10, h-20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return annotated

def main():
    global tracking, last_detection_time
    
    print(f"连接到Go2机器人: {GO2_ADDRESS}")
    
    try:
        # 初始化Go2客户端
        client = Go2ROS2Client(GO2_ADDRESS, COMMAND_PORT, STATE_PORT, IMG_PORT)
        
        # 初始化YOLO检测器
        detector = YoloMultiTask(YOLO_MODEL_PATH, task="detect")
        
        # 初始化PID控制器
        pid_x = PIDController(kp=0.5, ki=0.1, kd=0.05, dt=0.1, output_limits=(-0.5, 0.5))
        pid_y = PIDController(kp=0.8, ki=0.1, kd=0.1, dt=0.1, output_limits=(-0.8, 0.8))
        pid_yaw = PIDController(kp=1.0, ki=0.1, kd=0.1, dt=0.1, output_limits=(-1.0, 1.0))
        
        print(f"开始跟踪目标: {TARGET_CLASS}")
        print("按 'q' 退出，按 's' 开始/停止跟踪")
        
        while True:
            # 获取最新图像
            image = client.get_latest_image()
            
            if image is None:
                print("等待图像数据...")
                time.sleep(0.1)
                continue
            
            # 检测目标
            target_box = detect_target(detector, image, TARGET_CLASS)
            
            if target_box is not None:
                last_detection_time = time.time()
                
                if tracking:
                    # 计算控制命令
                    vx, vy, vyaw = calculate_control_commands(target_box, image.shape, 
                                                            pid_x, pid_y, pid_yaw)
                    
                    # 发送控制命令
                    client.send_move_command(vx, vy, vyaw)
                    
                    print(f"跟踪中 - vx: {vx:.2f}, vy: {vy:.2f}, vyaw: {vyaw:.2f}")
            else:
                # 检查是否超时
                if time.time() - last_detection_time > DETECTION_TIMEOUT:
                    if tracking:
                        # 停止机器人
                        client.send_move_command(0, 0, 0)
                        print("目标丢失，停止移动")
            
            # 绘制跟踪信息
            annotated_image = draw_tracking_info(image, target_box, tracking)
            
            # 显示图像
            cv2.imshow("Go2 Visual Tracking", annotated_image)
            
            # 处理按键
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                tracking = not tracking
                if not tracking:
                    client.send_move_command(0, 0, 0)  # 停止移动
                    # 重置PID控制器
                    pid_x.reset()
                    pid_y.reset()
                    pid_yaw.reset()
                print(f"跟踪状态: {'开启' if tracking else '关闭'}")
            
            time.sleep(0.1)  # 控制循环频率
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在退出...")
    except Exception as e:
        print(f"运行时错误: {e}")
    finally:
        # 停止机器人并清理资源
        try:
            client.send_move_command(0, 0, 0)
            client.close()
        except:
            pass
        cv2.destroyAllWindows()
        print("视觉跟踪系统已关闭")

if __name__ == '__main__':
    main()