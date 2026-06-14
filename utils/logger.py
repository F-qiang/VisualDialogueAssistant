import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import psutil


def get_logger(name: str = "visual_dialogue_assistant") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# PR17：TTS 配置管理
class TTSConfig:
    """TTS 语速和音量配置。"""

    def __init__(self):
        self.speed = 1.0  # 语速倍数 0.5-2.0
        self.volume = 100  # 音量百分比 0-100


# PR21：性能监控
class PerformanceMonitor:
    """系统性能监控。"""

    def __init__(self):
        self.request_times = []
        self.start_time = None
        self.last_request_latency = 0.0
        self.last_tts_success = True
        self.last_audio_ok = True

    def start_request(self):
        """请求开始。"""
        self.start_time = time.time()

    def end_request(self):
        """请求结束，记录耗时。"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.last_request_latency = elapsed
            self.request_times.append(elapsed)
            if len(self.request_times) > 1000:  # 只保留最近 1000 条
                self.request_times = self.request_times[-1000:]

    def set_tts_success(self, success: bool):
        """记录最近一次 TTS 是否成功。"""
        self.last_tts_success = success

    def set_audio_ok(self, ok: bool):
        """记录录音状态是否正常。"""
        self.last_audio_ok = ok

    def get_status(self) -> str:
        """根据最近一次请求耗时返回响应状态。"""
        latency = self.last_request_latency
        if latency <= 1.0:
            return "正常"
        if latency <= 3.0:
            return "较慢"
        return "卡顿"

    def get_metrics(self) -> dict:
        """获取性能指标。"""
        metrics = {
            "status": self.get_status(),
            "last_latency": self.last_request_latency,
            "tts_success": self.last_tts_success,
            "audio_ok": self.last_audio_ok,
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,
            "cpu_percent": psutil.Process().cpu_percent(interval=0.1),
        }
        if self.request_times:
            metrics.update({
                "avg_latency": sum(self.request_times) / len(self.request_times),
                "max_latency": max(self.request_times),
                "min_latency": min(self.request_times),
                "total_requests": len(self.request_times),
            })
        return metrics


# PR12：全局统计实例
class CostStats:
    """成本统计管理器。"""

    def __init__(self):
        self.llm_calls = 0
        self.vlm_calls = 0
        self.vision_cache_hits = 0
        self.summary_count = 0
        self.request_cache_hits = 0
        self.tts_config = TTSConfig()
        self.user_prefs = {}  # PR18：用户偏好
        self.perf_monitor = PerformanceMonitor()

    def record_llm_call(self):
        """记录 LLM 调用。"""
        self.llm_calls += 1
    
    def record_vlm_call(self):
        """记录 VLM 调用"""
        self.vlm_calls += 1
    
    def record_vision_cache_hit(self):
        """记录视觉缓存命中"""
        self.vision_cache_hits += 1
    
    def record_request_cache_hit(self):
        """记录请求缓存命中"""
        self.request_cache_hits += 1
    
    # PR17：TTS 配置接口
    def get_tts_config(self) -> dict:
        """获取 TTS 配置"""
        return {"speed": self.tts_config.speed, "volume": self.tts_config.volume}
    
    def set_tts_config(self, speed: float, volume: float):
        """设置 TTS 配置"""
        self.tts_config.speed = max(0.5, min(2.0, speed))
        self.tts_config.volume = max(0, min(100, volume))
    
    # PR18：用户偏好接口
    def record_model_choice(self, question_type: str, model_name: str):
        """记录用户对某类问题选择的模型"""
        if question_type not in self.user_prefs:
            self.user_prefs[question_type] = {"llm": 0, "vlm": 0}
        if model_name in self.user_prefs[question_type]:
            self.user_prefs[question_type][model_name] += 1
    
    def get_user_stats(self) -> dict:
        """获取用户统计"""
        return self.user_prefs
    
    # PR20：数据导出接口
    def export_to_json(self, filepath: str | Path):
        """导出为 JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "llm_calls": self.llm_calls,
            "vlm_calls": self.vlm_calls,
            "vision_cache_hits": self.vision_cache_hits,
            "request_cache_hits": self.request_cache_hits,
            "summary_count": self.summary_count,
            "user_preferences": self.user_prefs,
            "performance_metrics": self.perf_monitor.get_metrics()
        }
        Path(filepath).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    def export_to_csv(self, filepath: str | Path):
        """导出为 CSV"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["指标", "数值"])
            writer.writerow(["LLM 调用", self.llm_calls])
            writer.writerow(["VLM 调用", self.vlm_calls])
            writer.writerow(["视觉缓存命中", self.vision_cache_hits])
            writer.writerow(["请求缓存命中", self.request_cache_hits])
            writer.writerow(["上下文摘要", self.summary_count])
    
    # PR21：性能监控接口
    def get_performance_metrics(self) -> dict:
        """获取性能指标"""
        return self.perf_monitor.get_metrics()
    
    def get_summary(self) -> dict:
        """获取统计摘要"""
        total_api_calls = self.llm_calls + self.vlm_calls
        saved_calls = self.vision_cache_hits + self.request_cache_hits
        cost_saved = (saved_calls / max(total_api_calls, 1)) * 100 if total_api_calls > 0 else 0
        
        return {
            "llm_calls": self.llm_calls,
            "vlm_calls": self.vlm_calls,
            "vision_cache_hits": self.vision_cache_hits,
            "request_cache_hits": self.request_cache_hits,
            "summary_count": self.summary_count,
            "total_api_calls": total_api_calls,
            "cost_saved_percent": f"{cost_saved:.1f}%",
        }
    
    def clear(self):
        """清空统计"""
        self.llm_calls = 0
        self.vlm_calls = 0
        self.vision_cache_hits = 0
        self.summary_count = 0
        self.request_cache_hits = 0


# 全局统计实例
stats = CostStats()

