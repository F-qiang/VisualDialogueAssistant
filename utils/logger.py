import logging


def get_logger(name: str = "visual_dialogue_assistant") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# PR12：全局统计实例
class CostStats:
    """成本统计管理器"""
    def __init__(self):
        self.llm_calls = 0
        self.vlm_calls = 0
        self.vision_cache_hits = 0
        self.summary_count = 0
    
    def record_llm_call(self):
        """记录 LLM 调用"""
        self.llm_calls += 1
    
    def record_vlm_call(self):
        """记录 VLM 调用"""
        self.vlm_calls += 1
    
    def record_vision_cache_hit(self):
        """记录视觉缓存命中"""
        self.vision_cache_hits += 1
    
    def record_request_cache_hit(self):
        """记录请求缓存命中"""
        self.request_cache_hits = getattr(self, 'request_cache_hits', 0) + 1
    
    def get_summary(self) -> dict:
        """获取统计摘要"""
        total_api_calls = self.llm_calls + self.vlm_calls
        saved_calls = self.vision_cache_hits
        cost_saved = (saved_calls / max(total_api_calls, 1)) * 100 if total_api_calls > 0 else 0
        
        return {
            "llm_calls": self.llm_calls,
            "vlm_calls": self.vlm_calls,
            "vision_cache_hits": self.vision_cache_hits,
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


# 全局统计实例
stats = CostStats()

