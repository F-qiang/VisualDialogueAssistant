from __future__ import annotations

import cv2
import numpy as np


def compress_frame(frame: np.ndarray, max_width: int = 640, quality: int = 70) -> bytes:
    """
    压缩摄像头帧为 JPEG 字节。

    先将宽度缩放至 max_width（高度等比缩放），再以指定质量编码。
    统一压缩参数可确保单图体积可量化（约减少 70%）。

    :param frame: BGR 格式的原始帧。
    :param max_width: 目标宽度，默认 640px。
    :param quality: JPEG 压缩质量，默认 70。
    :return: JPEG 字节数据。
    """
    h, w = frame.shape[:2]
    if w > max_width:
        # 等比缩放，保持宽高比
        frame = cv2.resize(frame, (max_width, int(h * max_width / w)))
    success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        raise ValueError("图像压缩失败")
    return buffer.tobytes()


def check_brightness(frame: np.ndarray, threshold: int = 40) -> bool:
    """
    检测画面亮度是否充足。

    计算灰度图的平均像素值，低于阈值视为光线偏暗。

    :param frame: BGR 格式的原始帧。
    :param threshold: 亮度阈值，默认 40（0-255）。
    :return: True 表示亮度充足，False 表示光线偏暗。
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)) >= threshold


def check_sharpness(frame: np.ndarray, threshold: float = 100.0) -> bool:
    """
    检测画面清晰度是否充足。

    使用拉普拉斯算子计算方差，值越低表示画面越模糊。

    :param frame: BGR 格式的原始帧。
    :param threshold: 清晰度阈值，默认 100.0。
    :return: True 表示画面清晰，False 表示画面模糊。
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var()) >= threshold


def motion_detect(prev_frame: np.ndarray | None, curr_frame: np.ndarray | None) -> bool:
    """
    检测两帧之间是否有明显画面变化（预留接口，PR11 实现）。

    当前直接调用 detect_frame_change，PR11 可在此扩展更精细的运动检测。

    :param prev_frame: 上一帧，首次调用时为 None。
    :param curr_frame: 当前帧。
    :return: True 表示画面有明显变化。
    """
    return detect_frame_change(prev_frame, curr_frame)


def detect_frame_change(
    prev_frame: np.ndarray | None,
    current_frame: np.ndarray | None,
    threshold: float = 0.12,
) -> bool:
    """
    基于帧差法判断两帧之间是否有明显变化。

    计算灰度差异像素占比，超过阈值则认为画面发生变化。

    :param prev_frame: 上一帧。
    :param current_frame: 当前帧。
    :param threshold: 差异像素占比阈值，默认 0.12（12%）。
    :return: True 表示画面变化明显。
    """
    if prev_frame is None or current_frame is None:
        return False
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(prev_gray, curr_gray)
    return (np.count_nonzero(diff) / diff.size) > threshold
