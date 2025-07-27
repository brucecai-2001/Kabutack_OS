import cv2
import numpy as np
from typing import Union
from PIL import Image

import groundingdino.datasets.transforms as T
from groundingdino.util.inference import load_model, predict, annotate

class GroundingDINO:
    """
        Marrying DINO with Grounded Pre-Training for Open-Set Object Detection
        Github: https://github.com/IDEA-Research/GroundingDINO
        Arxiv: https://arxiv.org/abs/2303.05499
    """
    def __init__(self, model_config_path: str,
                       model_checkpoint_path: str, 
                       bert_base_uncased_path: str = None,
                       device: str = "cpu",
                       box_treshold = 0.35,
                       text_treshold = 0.25
                ):
        """
        Args:
            model_config_path (str): model config path
            model_checkpoint_path (str): model checkpoint path
            bert_base_uncased_path (str, optional): local path of bert_base_uncased
            device (str, optional): device. Defaults to "cpu".
            box_treshold (float, optional):  Defaults to 0.35.
            text_treshold (float, optional):  Defaults to 0.25.
        """
        self.model = load_model(model_config_path, model_checkpoint_path, bert_base_uncased_path, device)
        self.device = device
        self.box_treshold = box_treshold,
        self.text_treshold = text_treshold

        self.image_transform = T.Compose(
            [
                T.RandomResize([800], max_size=1333),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )

    def __call__(self, image: Union[str, np.ndarray], text_prompt: str):
        """
        Inference on local image
        Args:
            image_path (Union[str, PIL.Image, np.ndarray]): image path or np array
            text_prompt (str): prompt

        Returns:
            raw_image (np.ndarray): The source image. 
            boxes (tensor) : predicted grouned box (n, 4)
            logits (tensor) : prediction probilities (n, 1)
            phrases (list[str]): detected objects phrases
        """

        # load image
        if isinstance(image, str):
            # 处理图像路径
            image_source = Image.open(image).convert("RGB")
            raw_image = np.asarray(image_source)
            image_transformed, _ = self.image_transform(image_source, None)
            
        elif isinstance(image, np.ndarray):
            # 处理 numpy 数组类型的图像
            raw_image = image
            image_source = Image.fromarray(np.uint8(image))
            image_transformed = self.image_transform(image_source)
        
        else:
            raise TypeError("不支持的图像类型。必须是 str, np.ndarray")
            
        # run grounding dino inference
        boxes, logits, phrases = predict(
            model=self.model,
            image=image_transformed,
            caption=text_prompt,
            box_threshold=self.box_treshold,
            text_threshold=self.text_treshold,
            device=self.device
        )

        return raw_image, boxes, logits, phrases
    
    def annotate(self, raw_image, boxes, logits, phrases, output: str):
        """
        Args:
            raw_image (np.ndarray): The source image to be annotated.
            boxes (tensor) : predicted grouned box (n, 4)
            logits (tensor) : prediction probilities (n, 1)
            phrases (list[str]): detected objects phrases
            output (str): the annotated image path to be saved
        """
        annotated_frame = annotate(image_source=raw_image, boxes=boxes, logits=logits, phrases=phrases)
        cv2.imwrite(output, annotated_frame)

if __name__ == '__main__':
    pass