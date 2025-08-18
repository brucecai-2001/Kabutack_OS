import base64
import logging
import cv2
import numpy as np
from typing import Optional

def encode_opencv_to_base64(image_data):
    # 将图像编码为JPEG格式的字节数据
    _, image_encoded = cv2.imencode('.jpg', image_data)
    image_bytes = image_encoded.tobytes()

    # base64 编码
    image_bytes_base64 = base64.b64encode(image_bytes).decode("utf-8")

    return image_bytes_base64

def decode_image_from_b64(image_b64: str) -> Optional[np.ndarray]:
    """Decodes a base64 encoded image string to an OpenCV image."""
    if not image_b64:
        return None
    try:
        jpg_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(jpg_data, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            logging.warning("cv2.imdecode returned None for an image.")
        return frame
    except (TypeError, ValueError) as e:
        logging.error(f"Error decoding base64 image data: {e}")
        return None

def decode_image_from_JPEG_bytes(image_data: bytes) -> Optional[np.ndarray]:
    """Decodes JPEG image data from bytes to an OpenCV image."""
    if not image_data:
        return None
    try:
        np_arr = np.frombuffer(image_data, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            logging.warning("cv2.imdecode returned None for an image.")
        return frame
    except (TypeError, ValueError) as e:
        logging.error(f"Error decoding JPEG image data: {e}")
        return None