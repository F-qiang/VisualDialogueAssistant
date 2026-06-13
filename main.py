from pathlib import Path

from dotenv import load_dotenv

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

# 加载项目根目录下的 .env 文件，使环境变量在全局可用
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def main() -> None:
    """程序入口：初始化 Qt 应用并启动主窗口。"""
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
