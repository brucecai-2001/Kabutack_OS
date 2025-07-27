import numpy as np

from datetime import datetime
from ultralytics import YOLO, YOLOWorld

class YoloMultiTask:
    """
        Object Detecion model, yolo11 series and yolo-world
        ultralytics's document': https://docs.ultralytics.com/zh/models/yolo11/
    """
    def __init__(self, 
                 yolo_model:str,
                 task: str = "detect"
                ):
        """
        Args:
            yolo_model (str): model path
            task (str): detect, cls, pose, obb, world
        """
        if task not in ["detect", "cls", "pose", "obb", "world"]:
            raise ValueError(f"{task} is not in ['detect', 'cls', 'pose', 'obb', 'world'")
        
        # Load YOLO model
        if task == "world":
            self.model = YOLOWorld(yolo_model)
        else:
            self.model = YOLO(yolo_model)

        self.task = task

        print("🚀: YOLO is init")


    def __call__(self, img: str | np.ndarray, 
                       prompt: str = None, 
                       save: bool = False,
                       plot: bool = False
                ):
        """
        ref: https://docs.ultralytics.com/modes/predict/#inference-sources

        Args:
            img (str | np.ndarray): image, could be a local file, a url, a np.ndarray object
            prompt (str): text prompt for yolo world
        """
        # Inference
        if self.task == "world":
            self.model.set_classes([prompt])
            results = self.model(img)
        else:
            results = self.model(img)

        result = results[0]
        output = {}

        # Process results list
        if self.task in ["detect", "world"]:
            boxes_xyxy = result.boxes.xyxy  # top-left-x, top-left-y, bottom-right-x, bottom-right-y
            names = [result.names[cls.item()] for cls in result.boxes.cls.int()]  # class name of each box
            confs = result.boxes.conf  # confidence score of each box

            output = {
                "boxes_xyxy": boxes_xyxy,
                "names": names,
                "confidence": confs
            }
        
        elif self.task == "cls":
            # Probs object for classification outputs
            top5_names = [result.names[cls.item()] for cls in result.probs.top5] # names of the top 5 classes.
            top5_probs = result.probs.top5conf # Confidences of the top 5 classes.

            output = {
                "top5_names": top5_names,
                "natop5_probsmes": top5_probs
            }
            
        elif self.task == "pose":
            # Keypoints object for pose outputs
            xy = result.keypoints.xy # A list of keypoints in pixel coordinates represented as tensors.
            conf = result.keypoints.conf # confidence values of keypoints if available, else None.

            output = {
                "xy": xy,
                "confidence": conf,
            }

        else:
            raise ValueError(f"{self.task} is not in ['detect', 'cls', 'pose', 'obb', 'world'")

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result.save(f"src/result_{timestamp}.jpg")  # save to disk
            
        if plot:
            result.show()

        return output