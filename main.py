from pathlib import Path
import sys

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def main() -> None:
    """程序入口。"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
