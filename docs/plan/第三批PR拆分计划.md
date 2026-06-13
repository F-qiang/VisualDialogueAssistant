# 第三批 PR 拆分计划

## 一、拆分原则

第三批 PR 在第二批功能完整的基础上，聚焦**成本控制落地与演示体验提升**，对应赛题的核心加分项：

- 智能画面变化检测与视觉缓存，减少重复 VLM 调用
- 上下文摘要压缩，控制 Token 长度
- 请求缓存与复用，减少重复推理
- 实时成本统计展示，量化优化效果
- UI 美化与交互优化，提升演示体验

**设计原则**：每个 PR 只做一件事，单一职责，粒度细，易于审核。

---

## 二、第三批 PR 列表

### PR11：画面变化检测

**标题**：`[成本优化] 实现画面变化检测`

**功能描述**：
利用 `core/vision.py` 中的 `motion_detect()` 实现帧差法画面变化检测，判断用户提问时画面是否发生**明显变化**。为后续的视觉缓存和成本控制打基础。

**实现思路**：
1. 在 `core/vision.py` 中完善 `motion_detect()` 函数
   ```python
   def motion_detect(prev_frame, curr_frame, threshold=0.12):
       """检测两帧是否有明显变化"""
       return detect_frame_change(prev_frame, curr_frame, threshold)
   ```

2. 在 `core/pipeline.py` 中记录上一帧
   ```python
   self._prev_frame = None  # 上一帧
   
   def capture_frame(self):
       ret, frame = self.camera.read_frame()
       if ret:
           self._prev_frame = frame
       return ret
   ```

3. 在视觉路由前判断画面是否变化
   ```python
   if need_vision(text):
       changed = motion_detect(self._prev_frame, self._current_frame)
       if not changed:
           # 记录：画面未变，跳过新帧上传
           logger.info("画面未变，跳过新帧")
   ```

**测试方式**：
- 固定画面，连续提问两次，`motion_detect()` 应返回 False
- 移动摄像头后提问，`motion_detect()` 应返回 True

**影响范围**：
- `core/vision.py`（完善 `motion_detect`）
- `core/pipeline.py`（调用 `motion_detect`）

**合规同步动作**：
- README 补充画面变化检测说明

---

### PR12：视觉缓存机制

**标题**：`[成本优化] 实现视觉缓存，复用 VLM 结果`

**功能描述**：
当画面未发生变化时，直接复用上一次 VLM 的识别结果，无需重新调用 VLM。减少不必要的多模态 API 调用。

**实现思路**：
1. 在 `core/pipeline.py` 中加入视觉缓存
   ```python
   self._last_vision_result = None  # 缓存的 VLM 结果
   
   def process_audio(self, audio_path):
       if need_vision(text) and self._current_frame:
           if motion_detect(self._prev_frame, self._current_frame):
               # 画面变化，调用新的 VLM
               reply = self._vlm.chat_with_image(...)
               self._last_vision_result = reply
           else:
               # 画面未变，复用缓存
               reply = self._last_vision_result
   ```

2. 统计缓存命中次数
   ```python
   self._vision_cache_hits = 0
   if not motion_detect(...):
       self._vision_cache_hits += 1
   ```

**测试方式**：
- 固定画面，对摄像头提问"看一下"
- 再次对同一画面提问"这是什么"
- 第二次应该用缓存，不调用 VLM
- 统计应显示"缓存命中 1 次"

**影响范围**：
- `core/pipeline.py`（视觉缓存逻辑）
- `utils/logger.py`（统计缓存命中）

**合规同步动作**：
- README 补充视觉缓存说明

---

### PR13：上下文摘要压缩

**标题**：`[成本优化] 实现上下文摘要压缩`

**功能描述**：
当对话历史超出 `max_rounds` 时，自动调用 LLM 对旧对话进行摘要，将 N 轮对话压缩成一条背景消息，控制上下文 Token 长度。

**实现思路**：
1. 在 `core/context.py` 中新增摘要方法
   ```python
   def summarize_old_rounds(self):
       """当历史超出 max_rounds 时，摘要最旧的对话"""
       if len(self.history) > self.max_rounds * 2:
           old_rounds = self.history[:4]  # 前两轮
           summary = self._call_llm_summarize(old_rounds)
           # 用摘要替换旧对话
           self.history = [{"role": "system", "content": f"背景：{summary}"}] + self.history[4:]
   
   def _call_llm_summarize(self, rounds):
       """调用 LLM 生成摘要"""
       prompt = f"请摘要以下对话内容成一句话：{rounds}"
       return LLMClient().chat([{"role": "user", "content": prompt}])
   ```

2. 在 `process_audio()` 后调用摘要
   ```python
   self.ctx.add("user", text)
   self.ctx.add("assistant", reply)
   self.ctx.summarize_old_rounds()  # 自动摘要
   ```

3. 记录摘要次数
   ```python
   self._summary_count = 0
   if len(self.history) > self.max_rounds * 2:
       self._summary_count += 1
   ```

**测试方式**：
- 进行 10+ 轮对话
- 观察历史是否被压缩（前面的对话应被摘要）
- 摘要后的回答质量应不下降
- 统计应显示"摘要 N 次"

**影响范围**：
- `core/context.py`（摘要逻辑）
- `utils/logger.py`（统计摘要次数）

**合规同步动作**：
- README 补充上下文摘要说明

---

## 后续部分（PR14～PR16）待续...

---

### PR14：请求缓存与复用

**标题**：`[成本优化] 实现请求缓存，复用 LLM 结果`

**功能描述**：
缓存 LLM 和 VLM 的请求结果。相同的问题文本 + 相同的上下文在短时间内被重复提问时，直接返回缓存结果，无需重新调用 API。

**实现思路**：
1. 在 `core/router.py` 中新增缓存类
   ```python
   import hashlib
   from datetime import datetime, timedelta
   
   class RequestCache:
       def __init__(self, ttl_seconds=300):  # 5 分钟过期
           self.cache = {}
           self.ttl = ttl_seconds
       
       def get_key(self, text, context_hash):
           """生成缓存 key：问题 + 上下文哈希"""
           return hashlib.md5(f"{text}{context_hash}".encode()).hexdigest()
       
       def get(self, key):
           """获取缓存，检查是否过期"""
           if key in self.cache:
               result, timestamp = self.cache[key]
               if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                   return result
               else:
                   del self.cache[key]
           return None
       
       def set(self, key, result):
           """保存缓存"""
           self.cache[key] = (result, datetime.now())
       
       def clear(self):
           """清空缓存"""
           self.cache.clear()
   ```

2. 在 `core/pipeline.py` 中使用缓存
   ```python
   from core.router import RequestCache
   
   self._request_cache = RequestCache()
   
   def process_audio(self, audio_path):
       # ...ASR 识别...
       context_hash = hashlib.md5(str(self.ctx.get()).encode()).hexdigest()
       cache_key = self._request_cache.get_key(text, context_hash)
       
       # 先查缓存
       cached_reply = self._request_cache.get(cache_key)
       if cached_reply:
           self._cache_hits += 1
           return text, cached_reply, ""
       
       # 缓存未命中，调用 API
       reply = llm.chat(...) or vlm.chat_with_image(...)
       
       # 保存到缓存
       self._request_cache.set(cache_key, reply)
       return text, reply, tts_path
   ```

3. 提供清空缓存接口
   ```python
   def clear_request_cache(self):
       """清空请求缓存"""
       self._request_cache.clear()
   ```

**测试方式**：
- 提问"今天天气"，AI 返回回复 A
- 立即再次提问"今天天气"
- 应该直接返回缓存结果 A，不调用 API
- 统计应显示"缓存命中 1 次"
- 5 分钟后再问，应重新调用 API（缓存过期）

**影响范围**：
- `core/router.py`（缓存实现）
- `core/pipeline.py`（缓存调用）
- `utils/logger.py`（统计缓存命中）

**合规同步动作**：
- README 补充请求缓存说明

---

### PR15：成本统计面板

**标题**：`[成本优化] 实现成本统计面板`

**功能描述**：
在 `utils/logger.py` 中集中管理所有成本统计数据，在 `ui/main_window.py` 中新增成本统计面板，实时展示 API 调用次数、缓存命中率、成本节省等指标。

**实现思路**：
1. 在 `utils/logger.py` 中新增统计类
   ```python
   class CostStats:
       def __init__(self):
           self.llm_calls = 0        # LLM 调用次数
           self.vlm_calls = 0        # VLM 调用次数
           self.cache_hits = 0       # 缓存命中次数
           self.vision_cache_hits = 0 # 视觉缓存命中次数
           self.motion_skips = 0     # 画面变化检测跳过次数
           self.summary_count = 0    # 摘要压缩次数
       
       def get_summary(self):
           """获取统计摘要"""
           total_api_calls = self.llm_calls + self.vlm_calls
           cache_rate = (self.cache_hits / max(total_api_calls, 1)) * 100
           saved_calls = self.cache_hits + self.vision_cache_hits
           
           return {
               "total_llm": self.llm_calls,
               "total_vlm": self.vlm_calls,
               "cache_hits": self.cache_hits,
               "vision_cache_hits": self.vision_cache_hits,
               "cache_rate": f"{cache_rate:.1f}%",
               "saved_calls": saved_calls,
               "summary_count": self.summary_count,
               "cost_saved": f"{(saved_calls / max(total_api_calls, 1)) * 100:.1f}%"
           }
   
   # 全局统计实例
   stats = CostStats()
   ```

2. 在 `ui/main_window.py` 中新增统计面板
   ```python
   from utils.logger import stats
   
   # 新增统计标签
   self.stats_label = QLabel()
   self.stats_label.setStyleSheet("background: #f0f0f0; padding: 8px; border-radius: 4px;")
   
   # 定时更新统计
   self.stats_timer = QTimer(self)
   self.stats_timer.timeout.connect(self._update_stats)
   self.stats_timer.start(500)
   
   def _update_stats(self):
       """更新统计面板"""
       summary = stats.get_summary()
       text = f"""
       API 调用统计:
       LLM: {summary['total_llm']} | VLM: {summary['total_vlm']}
       缓存命中: {summary['cache_hits'] + summary['vision_cache_hits']}
       缓存命中率: {summary['cache_rate']}
       成本节省: {summary['cost_saved']}
       """
       self.stats_label.setText(text)
   ```

3. 在各 API 调用处记录统计
   ```python
   # 在 pipeline.py 中
   stats.llm_calls += 1  # LLM 调用 +1
   stats.vlm_calls += 1  # VLM 调用 +1
   stats.cache_hits += 1 # 缓存命中 +1
   ```

**测试方式**：
- 进行 5+ 轮对话
- 观察统计面板数据是否实时更新
- 缓存命中率、成本节省等数据应准确

**影响范围**：
- `utils/logger.py`（统计类）
- `ui/main_window.py`（统计面板）
- `core/pipeline.py`（统计埋点）

**合规同步动作**：
- README 补充成本统计说明

---

### PR16：UI 布局优化

**标题**：`[体验优化] UI 布局重组，提升视觉层次`

**功能描述**：
重新组织界面布局，将摄像头、对话、统计分开显示，提升用户体验。新增快捷操作按钮。

**实现思路**：
1. 新增布局结构
   - 左侧（40%）：摄像头预览
   - 右侧上（50%）：对话记录区
   - 右侧下（50%）：成本统计面板
   - 底部：按钮区

   ```python
   # 主布局
   main_layout = QHBoxLayout()
   
   # 左侧：摄像头
   left_layout = QVBoxLayout()
   left_layout.addWidget(self.video_label)
   left_layout.addWidget(self.status_label)
   
   # 右侧：对话 + 统计
   right_layout = QVBoxLayout()
   right_layout.addWidget(self.chat_box, 1)
   right_layout.addWidget(self.stats_label, 1)
   
   # 左右分配
   main_layout.addLayout(left_layout, 2)    # 40%
   main_layout.addLayout(right_layout, 3)   # 60%
   
   # 底部按钮
   button_layout = QHBoxLayout()
   button_layout.addWidget(self.record_btn)
   button_layout.addWidget(self.clear_btn)
   button_layout.addWidget(self.mode_btn)    # 新按钮：纯文本/视觉模式
   button_layout.addStretch()
   ```

2. 新增模式切换按钮
   ```python
   self.mode_btn = QPushButton("切换到纯文本模式")
   self.mode_btn.clicked.connect(self._toggle_mode)
   self._vision_mode = True  # 当前模式
   
   def _toggle_mode(self):
       """切换视觉模式和纯文本模式"""
       self._vision_mode = not self._vision_mode
       if self._vision_mode:
           self.mode_btn.setText("切换到纯文本模式")
       else:
           self.mode_btn.setText("切换到视觉模式")
   ```

3. 样式美化
   - 更清晰的分区颜色
   - 更大的字体
   - 更舒适的间距

**测试方式**：
- 验证布局在不同分辨率下是否清晰
- 摄像头、对话、统计是否都可见
- 按钮功能是否正常

**影响范围**：
- `ui/main_window.py`（布局重组）

**合规同步动作**：
- README 补充 UI 优化说明

---

## 三、第三批 PR 执行顺序

建议按顺序推进：

1. PR11：画面变化检测（基础）
2. PR12：视觉缓存（依赖 PR11）
3. PR13：上下文摘要（独立）
4. PR14：请求缓存（独立）
5. PR15：成本统计（依赖前面）
6. PR16：UI 优化（依赖前面）

---

## 四、第三批 PR 完成后的能力

| 能力 | PR |
|------|-----|
| 录音、识别、对话、播报 | 第一、二批 |
| 画面变化检测 | PR11 |
| 视觉缓存复用 | PR12 |
| 上下文摘要压缩 | PR13 |
| 请求缓存复用 | PR14 |
| 成本统计展示 | PR15 |
| UI 美化交互 | PR16 |
| **预期成本节省** | **30～50%** |

---

## 五、验收标准

### PR11
- ✅ 相同画面返回 False，移动后返回 True

### PR12
- ✅ 固定画面重复提问，第二次命中视觉缓存

### PR13
- ✅ 10+ 轮对话后，历史被自动摘要

### PR14
- ✅ 相同问题重复提问，第二次命中请求缓存

### PR15
- ✅ 统计面板实时显示准确数据

### PR16
- ✅ UI 布局清晰，各功能按钮正常

