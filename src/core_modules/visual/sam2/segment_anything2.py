import numpy as np
from ultralytics import SAM

class SAM2:
    """
        Large Semantic Segmentation Model
        ultralytics's document': https://docs.ultralytics.com/models/sam/#sam-prediction-example
    """
    def __init__(self, 
                 sam_model:str
                ):
        # Load a model
        self.model = SAM(sam_model)
        self.model_name = sam_model

        print("🚀: SAM2 is init")


    def __call__(self, img: str | np.ndarray, bboxes: list):
        """
        Args:
            img (str | np.ndarray): image
            bboxes (list): bounding box

        Returns:
            seg_mask: segmentation masks H x W
        """
        results = self.model.predict(img, bboxes=bboxes)
        if results:
            result = results[0]
            masks = result.masks
            if masks is not None:
                # 获取第一个掩码（numpy数组，shape为[H, W]，布尔值）
                seg_mask = masks.data[0].cpu().numpy().astype(np.uint8) * 255  # 转换为0-255的灰度图
                return seg_mask
            
        return seg_mask

# if __name__ == '__main__':
#     model = SAM2()
#     masks = model("tests/test_sam.jpeg", [300, 700, 700, 300])