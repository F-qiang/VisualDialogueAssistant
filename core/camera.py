import cv2

from app.config import CONFIG


class CameraService:
    def __init__(self, camera_index: int | None = None) -> None:
        self.camera_index = CONFIG.camera_index if camera_index is None else camera_index
        self.capture = None

    def open(self) -> bool:
        self.capture = cv2.VideoCapture(self.camera_index)
        return self.capture.isOpened()

    def read_frame(self):
        if self.capture is None:
            return False, None
        return self.capture.read()

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
