"""异常处理与降级模式。"""


class ServiceUnavailableError(Exception):
    """云端 AI 服务不可用异常。"""
    pass


def format_error_message(exc: Exception) -> str:
    """格式化异常消息供用户展示。"""
    return f"发生错误：{exc}"


def get_fallback_response(user_input: str) -> str:
    """
    当 AI 服务完全不可用时的降级回复。

    返回一个基于用户输入的简单回复，避免系统完全失能。
    """
    keywords = {
        "天气": "我无法获取实时天气信息，建议查看天气应用。",
        "时间": "请查看系统时间。",
        "帮助": "我现在功能受限，请稍后重试。",
    }
    for kw, resp in keywords.items():
        if kw in user_input:
            return resp
    return "我现在暂时无法应答，请检查网络连接或稍后重试。"
