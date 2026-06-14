from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

# 触发视觉问答的关键词列表
_VISION_KEYWORDS = [
    "画面", "场景", "环境", "背景", "摄像头", "屏幕", "显示器",
    "物体", "东西", "什么东西", "这是什么", "那是什么",
    "桌面", "桌上", "手里", "手上", "旁边", "前面", "后面",
    "人", "人物", "谁", "身上", "戴着", "穿着", "头发",
    "颜色", "形状", "大小", "样子", "外观",
    "光线", "亮度", "明亮", "暗",
    "看一下", "看看", "帮我看", "描述", "识别", "分析",
]


# PR13：请求缓存类
class RequestCache:
    """请求结果缓存，支持 TTL 过期。"""

    def __init__(self, ttl_seconds: int = 300):
        """初始化缓存。"""
        self.cache = {}
        self.ttl = ttl_seconds
        self._user_prefs = {}  # PR18：用户偏好
    
    def get_key(self, text: str, context_hash: str) -> str:
        """生成缓存 key"""
        key_str = f"{text}_{context_hash}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> str | None:
        """获取缓存，检查是否过期"""
        if key not in self.cache:
            return None
        
        result, timestamp = self.cache[key]
        if datetime.now() - timestamp < timedelta(seconds=self.ttl):
            return result
        else:
            del self.cache[key]
            return None
    
    def set(self, key: str, result: str) -> None:
        """保存缓存"""
        self.cache[key] = (result, datetime.now())
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def get_size(self) -> int:
        """获取缓存项数"""
        return len(self.cache)
    
    # PR18：用户偏好接口
    def add_preference(self, question_type: str, preferred_model: str):
        """添加用户偏好记录"""
        if question_type not in self._user_prefs:
            self._user_prefs[question_type] = {"llm": 0, "vlm": 0}
        if preferred_model in self._user_prefs[question_type]:
            self._user_prefs[question_type][preferred_model] += 1
    
    def get_preference(self, question_type: str) -> str | None:
        """获取某类问题的用户偏好"""
        if question_type not in self._user_prefs:
            return None
        prefs = self._user_prefs[question_type]
        if prefs["llm"] == 0 and prefs["vlm"] == 0:
            return None
        return "vlm" if prefs["vlm"] > prefs["llm"] else "llm"


def need_vision(question: str) -> bool:
    """判断用户提问是否需要视觉信息"""
    return any(kw in question for kw in _VISION_KEYWORDS)


def judge_need_vision(question: str) -> bool:
    """兼容旧接口"""
    return need_vision(question)
