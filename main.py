from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def main() -> None:
    """程序入口。"""
    print("AI 视觉对话助手启动中...")


if __name__ == "__main__":
    main()
