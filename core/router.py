from __future__ import annotations

# 触发视觉问答的关键词列表
# 当用户提问包含这些词时，路由到 VLM；否则路由到纯文本 LLM
_VISION_KEYWORDS = [
    # 画面与场景描述
    "画面", "场景", "环境", "背景", "摄像头", "屏幕", "显示器",
    # 物体与位置
    "物体", "东西", "什么东西", "这是什么", "那是什么",
    "桌面", "桌上", "手里", "手上", "旁边", "前面", "后面",
    # 人物与识别
    "人", "人物", "谁", "身上", "戴着", "穿着", "头发",
    # 视觉属性
    "颜色", "形状", "大小", "样子", "外观",
    "光线", "亮度", "明亮", "暗",
    # 动作指令
    "看一下", "看看", "帮我看", "描述", "识别", "分析",
]


def need_vision(question: str) -> bool:
    """
    判断用户提问是否需要视觉信息。

    通过关键词匹配快速分类，命中任意一个关键词则路由到 VLM，
    否则路由到纯文本 LLM，减少不必要的图像上传和多模态调用成本。

    :param question: 用户当前提问文字。
    :return: True 表示需要视觉，False 表示纯文本即可。
    """
    return any(kw in question for kw in _VISION_KEYWORDS)


def judge_need_vision(question: str) -> bool:
    """兼容旧接口，内部调用 need_vision。"""
    return need_vision(question)
