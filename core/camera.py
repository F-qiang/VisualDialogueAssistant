import cv2

from app.config import CONFIG


class CameraService:
    """
    摄像头采集服务。

    负责打开摄像头、逐帧读取画面和释放资源。
    界面层通过 read_frame() 获取当前帧，推理层通过同一方法截取关键帧。
    """

    def __init__(self, camera_index: int | None = None) -> None:
        # 优先使用传入的设备索引，否则从全局配置读取
        self.camera_index = CONFIG.camera_index if camera_index is None else camera_index
        self.capture = None  # cv2.VideoCapture 实例，未打开时为 None

    def open(self) -> bool:
        """打开摄像头，返回是否成功。"""
        self.capture = cv2.VideoCapture(self.camera_index)
        return self.capture.isOpened()

    def read_frame(self):
        """
        读取一帧画面。

        返回 (ret, frame)，与 cv2.VideoCapture.read() 格式一致。
        摄像头未打开时返回 (False, None)。
        """
        if self.capture is None:
            return False, None
        return self.capture.read()

    def release(self) -> None:
        """释放摄像头资源，防止设备被占用。"""
        if self.capture is not None:
            self.capture.release()
            self.capture = None
