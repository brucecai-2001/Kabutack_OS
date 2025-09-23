import argparse
import time
import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

from src.hardware_interface.go2 import Go2Robot
from src.core_modules.visual.grounding_dino.groundingd_dino import GroundingDINO
from src.core_modules.visual.co_tracker.co_tracker import CoTrackerCamera

class Go2VisualTracker:
    def __init__(self, target_object: str, tracking_speed: float = 0.5) -> None:
        """
        初始化Go2视觉跟踪器
        
        Args:
            target_object: 要跟踪的目标物体名称
            tracking_speed: 跟踪速度系数 (0.0-1.0)
        """
        self.target_object = target_object
        self.tracking_speed = max(0.0, min(1.0, tracking_speed))  # 限制在0-1范围内
        
        # 初始化机器人
        self.robot = Go2Robot()
        
        # 初始化视觉模型
        self.detector = GroundingDINO()
        self.tracker = CoTrackerCamera()
        
        # 跟踪状态
        self.tracking_active = False
        self.target_bbox = None  # [x1, y1, x2, y2]
        self.track_points = None  # 跟踪点
        self.prev_frame = None  # 上一帧图像
        
        print(f"Go2VisualTracker initialized. Target object: {target_object}")
    
    def initialize(self) -> None:
        """初始化机器人和视觉模型"""
        try:
            # 初始化机器人
            self.robot.initialize()
            time.sleep(2)  # 等待机器人初始化完成
            
            print("Go2VisualTracker ready. Press Ctrl+C to stop.")
        except Exception as e:
            print(f"Failed to initialize Go2VisualTracker: {e}")
            self.shutdown()
            raise
    
    def shutdown(self) -> None:
        """关闭所有资源"""
        print("Shutting down Go2VisualTracker...")
        self.tracking_active = False
        
        # 关闭机器人
        if hasattr(self, 'robot'):
            self.robot.shutdown()
        
        cv2.destroyAllWindows()
        print("Go2VisualTracker shutdown completed.")
    
    def detect_target(self, frame: np.ndarray) -> Optional[List[float]]:
        """
        使用GroundingDINO检测目标物体
        
        Args:
            frame: 输入图像
            
        Returns:
            检测到的目标边界框 [x1, y1, x2, y2] 或 None
        """
        if frame is None:
            return None
        
        # 使用GroundingDINO检测目标
        detections = self.detector.detect(frame, text_prompt=self.target_object)
        
        # 如果检测到目标，返回置信度最高的边界框
        if detections and len(detections) > 0:
            # 获取置信度最高的检测结果
            best_detection = max(detections, key=lambda x: x['score'])
            if best_detection['score'] > 0.5:  # 置信度阈值
                return best_detection['bbox']  # [x1, y1, x2, y2]
        
        return None
    
    def initialize_tracking(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """
        初始化CoTracker跟踪器
        
        Args:
            frame: 输入图像
            bbox: 目标边界框 [x1, y1, x2, y2]
            
        Returns:
            是否成功初始化跟踪
        """
        if frame is None or bbox is None:
            return False
        
        try:
            # 在边界框内均匀采样跟踪点
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            
            # 确保边界框在图像范围内
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w-1, x2), min(h-1, y2)
            
            # 在目标区域内生成跟踪点
            grid_size = 5
            x_points = np.linspace(x1, x2, grid_size)
            y_points = np.linspace(y1, y2, grid_size)
            
            track_points = []
            for y in y_points:
                for x in x_points:
                    track_points.append([x, y])
            
            # 初始化跟踪器
            self.track_points = np.array(track_points)
            self.prev_frame = frame.copy()
            self.target_bbox = bbox
            self.tracking_active = True
            
            return True
        except Exception as e:
            print(f"Failed to initialize tracking: {e}")
            return False
    
    def update_tracking(self, frame: np.ndarray) -> Optional[List[float]]:
        """
        更新跟踪状态
        
        Args:
            frame: 当前帧图像
            
        Returns:
            更新后的目标边界框 [x1, y1, x2, y2] 或 None
        """
        if not self.tracking_active or frame is None or self.prev_frame is None:
            return None
        
        try:
            # 使用CoTracker更新跟踪点
            tracked_points = self.tracker.track(
                self.prev_frame, 
                frame, 
                self.track_points
            )
            
            # 更新跟踪点和上一帧
            self.track_points = tracked_points
            self.prev_frame = frame.copy()
            
            # 计算新的边界框
            if len(tracked_points) > 0:
                x_coords = tracked_points[:, 0]
                y_coords = tracked_points[:, 1]
                
                # 过滤掉异常值
                valid_indices = np.where(
                    (x_coords >= 0) & (x_coords < frame.shape[1]) &
                    (y_coords >= 0) & (y_coords < frame.shape[0])
                )[0]
                
                if len(valid_indices) > 0:
                    x_min = np.min(x_coords[valid_indices])
                    y_min = np.min(y_coords[valid_indices])
                    x_max = np.max(x_coords[valid_indices])
                    y_max = np.max(y_coords[valid_indices])
                    
                    # 更新目标边界框
                    self.target_bbox = [x_min, y_min, x_max, y_max]
                    return self.target_bbox
            
            # 如果跟踪失败，返回None
            return None
        except Exception as e:
            print(f"Tracking update failed: {e}")
            self.tracking_active = False
            return None
    
    def calculate_control_commands(self, frame: np.ndarray, bbox: List[float]) -> Tuple[float, float, float]:
        """
        根据目标位置计算控制命令
        
        Args:
            frame: 当前帧图像
            bbox: 目标边界框 [x1, y1, x2, y2]
            
        Returns:
            控制命令 (vx, vy, vyaw)
        """
        if frame is None or bbox is None:
            return 0.0, 0.0, 0.0
        
        # 计算目标中心点
        x1, y1, x2, y2 = bbox
        target_center_x = (x1 + x2) / 2
        target_center_y = (y1 + y2) / 2
        
        # 计算图像中心
        frame_height, frame_width = frame.shape[:2]
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2
        
        # 计算目标相对于中心的偏移
        offset_x = target_center_x - frame_center_x
        offset_y = target_center_y - frame_center_y
        
        # 归一化偏移量
        norm_offset_x = offset_x / (frame_width / 2)
        norm_offset_y = offset_y / (frame_height / 2)
        
        # 计算目标大小占比
        target_width = x2 - x1
        target_height = y2 - y1
        size_ratio = (target_width * target_height) / (frame_width * frame_height)
        
        # 计算控制命令
        # 水平偏移控制旋转
        vyaw = -norm_offset_x * 0.5 * self.tracking_speed
        
        # 前进速度基于目标大小
        vx = 0.0
        if size_ratio < 0.1:  # 目标太小，需要靠近
            vx = 0.3 * self.tracking_speed
        elif size_ratio > 0.3:  # 目标太大，需要后退
            vx = -0.2 * self.tracking_speed
        
        # 侧向移动基于水平偏移
        vy = 0.0
        if abs(norm_offset_x) > 0.3:  # 如果水平偏移较大，使用侧向移动辅助
            vy = norm_offset_x * 0.2 * self.tracking_speed
        
        # 限制命令范围
        vx = max(-0.5, min(0.5, vx))
        vy = max(-0.3, min(0.3, vy))
        vyaw = max(-0.8, min(0.8, vyaw))
        
        return vx, vy, vyaw
    
    def visualize(self, frame: np.ndarray, bbox: Optional[List[float]] = None) -> np.ndarray:
        """
        可视化跟踪结果
        
        Args:
            frame: 输入图像
            bbox: 目标边界框 [x1, y1, x2, y2]
            
        Returns:
            可视化后的图像
        """
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        vis_frame = frame.copy()
        
        # 绘制目标边界框
        if bbox is not None:
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(vis_frame, self.target_object, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 绘制跟踪点
        if self.tracking_active and self.track_points is not None:
            for point in self.track_points:
                x, y = int(point[0]), int(point[1])
                if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                    cv2.circle(vis_frame, (x, y), 2, (0, 0, 255), -1)
        
        # 添加状态信息
        status_text = f"Tracking: {'Active' if self.tracking_active else 'Inactive'}"
        cv2.putText(vis_frame, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return vis_frame
    
    def run(self) -> None:
        """运行视觉跟踪主循环"""
        try:
            self.initialize()
            
            detection_interval = 30  # 每30帧进行一次检测
            frame_count = 0
            
            while True:
                # 获取机器人观测数据
                observation = self.robot.get_observation()
                
                # 从观测中获取图像
                if observation["front_image"] is None:
                    print("No image available")
                    time.sleep(0.1)
                    continue
                
                # 解码Base64图像
                image_data = np.frombuffer(observation["front_image"], dtype=np.uint8)
                frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                # 如果没有激活跟踪或者需要重新检测
                if not self.tracking_active or frame_count % detection_interval == 0:
                    # 检测目标
                    bbox = self.detect_target(frame)
                    
                    if bbox is not None:
                        # 初始化或重新初始化跟踪
                        self.initialize_tracking(frame, bbox)
                        print(f"Target {self.target_object} detected and tracking initialized")
                
                # 更新跟踪
                if self.tracking_active:
                    bbox = self.update_tracking(frame)
                    
                    if bbox is not None:
                        # 计算控制命令
                        vx, vy, vyaw = self.calculate_control_commands(frame, bbox)
                        
                        # 发送控制命令到机器人
                        self.robot.move(vx, vy, vyaw)
                        
                        print(f"Tracking: vx={vx:.2f}, vy={vy:.2f}, vyaw={vyaw:.2f}")
                    else:
                        # 跟踪失败，停止机器人
                        self.robot.move(0.0, 0.0, 0.0)
                        self.tracking_active = False
                        print("Tracking lost")
                
                # 可视化
                vis_frame = self.visualize(frame, self.target_bbox if self.tracking_active else None)
                cv2.imshow("Go2 Visual Tracking", vis_frame)
                
                # 按ESC键退出
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
                
                frame_count += 1
                
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            self.shutdown()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Go2 Visual Tracking")
    parser.add_argument("--target", type=str, default="person",
                        help="Target object to track (default: person)")
    parser.add_argument("--speed", type=float, default=0.5,
                        help="Tracking speed factor (0.0-1.0, default: 0.5)")
    args = parser.parse_args()
    
    tracker = Go2VisualTracker(target_object=args.target, tracking_speed=args.speed)
    tracker.run()

if __name__ == "__main__":
    main()