import base64
import logging
import cv2
import numpy as np
from typing import Optional

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