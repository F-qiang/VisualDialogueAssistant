def judge_need_vision(question: str) -> bool:
    vision_keywords = ["画面", "物体", "桌面", "手里", "光线", "颜色", "这是什么", "看一下"]
    return any(keyword in question for keyword in vision_keywords)
