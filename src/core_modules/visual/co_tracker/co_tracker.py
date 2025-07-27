import cv2
import torch
import numpy as np
import pyarrow as pa

from collections import deque
from cotracker.utils.visualizer import Visualizer
from cotracker.predictor import CoTrackerOnlinePredictor

class CoTrackerCamera:
    """
        Simpler and Better Point Tracking by Pseudo-Labelling Real Videos
        Arxiv: https://arxiv.org/abs/2410.11831
        Dora-cotracker: https://github.com/dora-rs/dora/blob/main/node-hub/dora-cotracker/dora_cotracker/main.py
    """
    def __init__(self, checkpoint: str, interactive_mode: bool = False, camera_id: int = None, window_len=16):

        # Initialize CoTracker
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CoTrackerOnlinePredictor(checkpoint=checkpoint, window_len=window_len)
        self.buffer_size = self.model.step * 2
        self.window_frames = deque(maxlen=self.buffer_size)
        self.is_first_step = True
        self.accept_new_points = True
        self.clicked_points = []
        self.input_points = []
        self.input_masks = None

        # Initialize Camera
        self.interactive_mode = interactive_mode
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise ValueError(f"无法打开摄像头 {camera_id}")
        
        print("🚀: CoTrackerCamera is init")

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_points.append([x, y])
            self.is_first_step = True
            print(f"Clicked point added at: ({x}, {y})")

    def draw_tracking_points(self, tracks, visibility, frame_viz, num_input_stream):
        # Draw input points in red
        for i, (pt, vis) in enumerate(
            zip(tracks[:num_input_stream], visibility[:num_input_stream])
        ):
            if vis > 0.5:
                x, y = int(pt[0]), int(pt[1])
                cv2.circle(
                    frame_viz, (x, y), radius=3, color=(0, 255, 0), thickness=-1
                )
                cv2.putText(
                    frame_viz,
                    f"I{i}",
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

        # Draw clicked points in red
        for i, (pt, vis) in enumerate(
            zip(tracks[num_input_stream:], visibility[num_input_stream:])
        ):
            if vis > 0.5:
                x, y = int(pt[0]), int(pt[1])
                cv2.circle(
                    frame_viz, (x, y), radius=3, color=(0, 0, 255), thickness=-1
                )
                cv2.putText(
                    frame_viz,
                    f"C{i}",
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    1,
                )

    def predict(self):
        """
            Process frame for tracking
        """
        # process input tracking points
        all_points = self.input_points + self.clicked_points
        print(all_points)
        if not all_points:
            return None, None, None
        
        query_points = torch.tensor(all_points, device=self.device).float()
        time_dim = torch.zeros(len(all_points), 1, device=self.device)
        queries = torch.cat([time_dim, query_points], dim=1).unsqueeze(0)
            
        # stack window frames to a video
        video_chunk = torch.tensor(
            np.stack(list(self.window_frames)), device=self.device
        ).float()
        video_chunk = video_chunk / 255.0
        video_chunk = video_chunk.permute(0, 3, 1, 2)[None] # Reshape to [B,T,C,H,W]

        # predict track points
        pred_tracks, pred_visibility = self.model(
            video_chunk,
            queries=queries,
            is_first_step=self.is_first_step,
            grid_size=0,
            add_support_grid=False,
        )
        self.is_first_step = False

        # process tracks points
        if pred_tracks is not None and pred_visibility is not None:
            self.accept_new_points = True
            tracks = pred_tracks[0, -1].cpu().numpy()
            visibility = pred_visibility[0, -1].cpu().numpy()

            # filter visible tracks points
            visible_tracks = []
            for pt, vis in zip(tracks, visibility):
                if vis > 0.5:
                    visible_tracks.append([int(pt[0]), int(pt[1])])
            visible_tracks = np.array(visible_tracks, dtype=np.float32)
            
            return tracks, visibility, visible_tracks
        

        return None, None, None

    def tracking(self, tracking_type, tracking_input):
        """
            Main run loop
            Args:
                tracking_type (str): track points | bbox | masks
        """

        if self.interactive_mode:
            cv2.namedWindow("Interactive Feed to track point", cv2.WINDOW_NORMAL)
            cv2.setMouseCallback("Interactive Feed to track point", self.mouse_callback)

        # set input_points
        if tracking_type == "points":
            points_array = tracking_input
            self.input_points = points_array.reshape((-1, 2)).tolist()

        elif tracking_type == "bbox":
            boxes2d = tracking_input
            # 对于每一个边界框，都会生成 3 个点，这些点处于边界框中间的垂直区域。
            self.input_points = [
                        [
                            int(x_min + (x_max - x_min) * 2 / 4),
                            int(y_min + (y_max - y_min) * i / 10),
                        ]
                        for i in range(4, 7)
                        for x_min, y_min, x_max, y_max in boxes2d
                    ]
        else:
            raise ValueError(f"Not a valid input type")
        
        self.is_first_step = True
        self.accept_new_points = True

        while True:
            # 读取一帧
            _, frame = self.cap.read()
            frame_viz = frame.copy()
            self.window_frames.append(frame)

            if len(self.window_frames) == self.buffer_size:
                pred_tracks, pred_visibility, visible_tracks = self.predict()
                if pred_tracks is not None and pred_visibility is not None:
                    print("test")
                    self.draw_tracking_points(pred_tracks, pred_visibility, frame_viz, len(self.input_points))
            
            # optional: add tracking point manually
            if self.interactive_mode:
                cv2.imshow("Interactive Feed to track point", frame)
                cv2.waitKey(1)

            if not self.accept_new_points:
                continue

# if __name__ == "__main__":
#     cotracker = CoTrackerCamera(checkpoint="checkpoints/cotracker/scaled_online.pth", interactive_mode=True, camera_id=0)
#     cotracker.tracking(tracking_type="points", tracking_input=np.array([[1000, 200], [800, 800]]))