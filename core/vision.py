from __future__ import annotations

import cv2
import numpy as np


def compress_frame(frame, quality: int = 70) -> bytes:
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode('.jpg', frame, encode_params)
    if not success:
        raise ValueError('图像压缩失败')
    return buffer.tobytes()


def detect_frame_change(prev_frame, current_frame, threshold: float = 0.12) -> bool:
    if prev_frame is None or current_frame is None:
        return False
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(prev_gray, curr_gray)
    ratio = np.count_nonzero(diff) / diff.size
    return ratio > threshold
