# 第四批 PR 拆分计划

## 一、定位与原则

第四批 PR 在第三批成本优化完成后，聚焦于**用户体验增强与系统健壮性**。

设计原则：
- 每个 PR 只做一件事，单一职责
- 充分利用第三批预留的接口
- 优先实现对演示效果影响最大的功能

---

## 二、预留接口需求

为了让第四批 PR 顺利实现，第三批 PR 需要预留以下接口：

### 在 `utils/logger.py` 中预留
```python
class CostStats:
    # 为 TTS 控制预留（PR17）
    def get_tts_config(self):
        """获取 TTS 配置：速度、音量等"""
        pass
    
    def set_tts_config(self, speed, volume):
        """设置 TTS 配置"""
        pass
    
    # 为用户偏好预留（PR18）
    def record_model_choice(self, question_type, model_name):
        """记录用户对某类问题选择的模型"""
        pass
    
    # 为数据导出预留（PR20）
    def export_to_file(self, filename, format="json"):
        """导出统计数据到文件"""
        pass
    
    # 为性能监控预留（PR21）
    def get_performance_metrics(self):
        """获取性能指标（响应时间、延迟等）"""
        pass
```

### 在 `core/router.py` 中预留
```python
class RequestCache:
    # 为用户偏好学习预留（PR18）
    def add_preference(self, question_type, preferred_model):
        """添加用户偏好记录"""
        pass
    
    def get_preference(self, question_type):
        """获取某类问题的用户偏好"""
        pass
```

### 在 `ui/main_window.py` 中预留
```python
class MainWindow:
    # 为 TTS 控制预留（PR17）
    def setup_tts_control_panel(self):
        """初始化 TTS 控制面板"""
        pass
    
    # 为用户偏好设置预留（PR19）
    def setup_preference_settings(self):
        """初始化用户偏好设置界面"""
        pass
    
    # 为性能监控预留（PR21）
    def setup_performance_panel(self):
        """初始化性能监控面板"""
        pass
```

---

## 三、第四批 PR 详细规划

### PR17：TTS 打断与语速控制

**标题**：`[交互优化] 实现 TTS 打断与语速控制`

**功能描述**：
增强 TTS 播报的交互性：支持用户在播报中按空格打断，支持调节语速（0.5～2.0 倍）和音量（0～100%）。

**实现思路**：
1. 在 `services/tts_client.py` 中新增速度和音量参数
   ```python
   def synthesize(self, text: str, output_path: str | Path, 
                  speed: float = 1.0, volume: float = 100):
       """合成语音，支持速度和音量调节"""
       # 调用百度 TTS API 时传入参数
       ```

2. 在 `ui/main_window.py` 中新增 TTS 控制面板
   ```python
   # TTS 速度滑块
   self.speed_slider = QSlider(Qt.Horizontal)
   self.speed_slider.setRange(50, 200)  # 0.5 ~ 2.0 倍
   self.speed_slider.setValue(100)
   
   # TTS 音量滑块
   self.volume_slider = QSlider(Qt.Horizontal)
   self.volume_slider.setRange(0, 100)
   self.volume_slider.setValue(100)
   
   # 打断按钮或快捷键
   def on_space_pressed(self):
       """按空格打断 TTS 播放"""
       os.system("taskkill /f /im wmplayer.exe")  # Windows
   ```

3. 在 `core/pipeline.py` 中传入参数
   ```python
   speed = stats.get_tts_config()['speed'] / 100
   volume = stats.get_tts_config()['volume']
   tts_file = self._tts.synthesize(reply, speed=speed, volume=volume)
   ```

**预留接口（为 PR22 日志系统）**：
```python
def log_tts_event(event_type, speed, volume, interrupted=False):
    """记录 TTS 事件（播放、打断、速度调整等）"""
    pass
```

**测试方式**：
- 调节速度滑块，TTS 播放速度应变化
- 调节音量滑块，TTS 音量应变化
- 按空格应打断播放

**影响范围**：
- `services/tts_client.py`（支持参数）
- `ui/main_window.py`（控制面板）
- `core/pipeline.py`（传参）

---

### PR18：用户偏好学习

**标题**：`[智能化] 实现用户偏好学习与自适应路由`

**功能描述**：
记录用户的行为偏好（比如用户经常问视觉问题或纯文本问题），系统学习后自动优化路由策略。

**实现思路**：
1. 定义问题类型分类
   ```python
   QUESTION_TYPES = {
       "vision": ["看", "这是什么", "屏幕"],
       "text": ["天气", "几点", "能做什么"],
       "mixed": ["对话", "聊天"]
   }
   ```

2. 在 `core/router.py` 中加入用户偏好学习
   ```python
   def classify_question(self, text):
       """分类问题类型"""
       for q_type, keywords in QUESTION_TYPES.items():
           if any(kw in text for kw in keywords):
               return q_type
       return "mixed"
   
   def get_preferred_model(self, q_type):
       """获取用户对该类问题的偏好模型"""
       pref = self._user_prefs.get(q_type)
       if pref:
           return pref  # 返回用户偏好的模型
       else:
           return self._default_route(q_type)  # 返回默认路由
   
   def record_choice(self, q_type, chosen_model):
       """记录用户的选择"""
       if q_type not in self._user_prefs:
           self._user_prefs[q_type] = {"llm": 0, "vlm": 0}
       self._user_prefs[q_type][chosen_model] += 1
   ```

3. 在 `core/pipeline.py` 中使用偏好
   ```python
   q_type = router.classify_question(text)
   preferred = router.get_preferred_model(q_type)
   
   if preferred == "vlm" and need_vision(text):
       reply = vlm.chat_with_image(...)
   else:
       reply = llm.chat(...)
   ```

**预留接口（为 PR19 动态参数调节）**：
```python
def get_user_stats(self):
    """获取用户偏好统计"""
    return self._user_prefs

def reset_preferences(self):
    """重置用户偏好"""
    self._user_prefs.clear()
```

**测试方式**：
- 提 5 个视觉问题
- 系统应倾向于使用 VLM
- 提 5 个文本问题
- 系统应倾向于使用 LLM

**影响范围**：
- `core/router.py`（偏好学习）
- `core/pipeline.py`（使用偏好）
- `utils/logger.py`（记录偏好）

---

### PR19：动态参数调节

**标题**：`[自适应] 实现动态参数调节与性能优化`

**功能描述**：
根据系统性能和用户反馈，自动调节关键参数（缓存过期时间、画面变化阈值、摘要长度等），优化系统行为。

**实现思路**：
1. 定义可调节参数
   ```python
   class DynamicParams:
       def __init__(self):
           self.cache_ttl = 300  # 缓存过期时间（秒）
           self.motion_threshold = 0.12  # 画面变化阈值
           self.brightness_threshold = 40  # 亮度阈值
           self.sharpness_threshold = 30  # 清晰度阈值
           self.summary_max_rounds = 5  # 摘要触发轮数
   ```

2. 在 `ui/main_window.py` 中新增参数调节面板
   ```python
   # 缓存过期时间滑块
   self.cache_ttl_slider = QSlider(Qt.Horizontal)
   self.cache_ttl_slider.setRange(60, 3600)
   self.cache_ttl_slider.setValue(300)
   
   # 画面变化阈值滑块
   self.motion_threshold_slider = QSlider(Qt.Horizontal)
   self.motion_threshold_slider.setRange(1, 50)  # 0.01 ~ 0.50
   self.motion_threshold_slider.setValue(12)
   
   def on_param_changed(self):
       """参数改变后更新系统"""
       params.cache_ttl = self.cache_ttl_slider.value()
       params.motion_threshold = self.motion_threshold_slider.value() / 100
   ```

3. 性能反馈触发调节
   ```python
   def auto_adjust_params(self):
       """根据性能指标自动调节参数"""
       avg_latency = stats.get_avg_latency()
       
       if avg_latency > 5:  # 响应时间 > 5秒
           # 降低阈值，增加缓存命中
           params.motion_threshold -= 0.01
           params.cache_ttl += 60
       elif avg_latency < 1:  # 响应时间 < 1秒
           # 提高标准
           params.motion_threshold += 0.01
   ```

**预留接口（为 PR21 性能监控）**：
```python
def get_current_params(self):
    """获取当前参数设置"""
    return vars(self)

def reset_to_defaults(self):
    """重置为默认参数"""
    pass
```

**测试方式**：
- 手动调节参数，确认生效
- 观察性能变化是否符合预期
- 检查自动调节是否合理

**影响范围**：
- `ui/main_window.py`（参数面板）
- `core/vision.py`（使用新阈值）
- `core/router.py`（使用新 TTL）

---

## 待续：PR20～PR22...

---

### PR20：统计数据导出

**标题**：`[数据分析] 实现统计数据导出与使用报告生成`

**功能描述**：
将成本统计、用户偏好、性能指标等数据导出为 JSON/CSV/Excel 格式，生成可视化的使用报告。

**实现思路**：
1. 在 `utils/logger.py` 中新增导出方法
   ```python
   import json
   import csv
   from datetime import datetime
   
   class CostStats:
       def export_to_json(self, filepath):
           """导出为 JSON"""
           data = {
               "timestamp": datetime.now().isoformat(),
               "llm_calls": self.llm_calls,
               "vlm_calls": self.vlm_calls,
               "cache_hits": self.cache_hits,
               "vision_cache_hits": self.vision_cache_hits,
               "summary_count": self.summary_count,
               "cost_saved_percent": self._calculate_savings(),
               "user_preferences": router.get_user_stats(),
               "performance_metrics": self._get_perf_metrics()
           }
           with open(filepath, 'w', encoding='utf-8') as f:
               json.dump(data, f, indent=2, ensure_ascii=False)
       
       def export_to_csv(self, filepath):
           """导出为 CSV"""
           with open(filepath, 'w', newline='', encoding='utf-8') as f:
               writer = csv.writer(f)
               writer.writerow(["指标", "数值"])
               writer.writerow(["LLM 调用", self.llm_calls])
               writer.writerow(["VLM 调用", self.vlm_calls])
               writer.writerow(["缓存命中", self.cache_hits])
               writer.writerow(["成本节省", f"{self._calculate_savings()}%"])
   ```

2. 在 `ui/main_window.py` 中新增导出按钮
   ```python
   self.export_btn = QPushButton("导出报告")
   self.export_btn.clicked.connect(self._export_report)
   
   def _export_report(self):
       """导出使用报告"""
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       
       # 导出为三种格式
       stats.export_to_json(f"report_{timestamp}.json")
       stats.export_to_csv(f"report_{timestamp}.csv")
       self._generate_html_report(f"report_{timestamp}.html")
       
       self.status_label.setText("报告已导出")
   
   def _generate_html_report(self, filepath):
       """生成 HTML 可视化报告"""
       html = f"""
       <html>
       <head><title>使用报告</title></head>
       <body>
       <h1>AI 视觉对话助手 - 使用报告</h1>
       <p>生成时间：{datetime.now()}</p>
       <h2>API 调用统计</h2>
       <ul>
           <li>LLM 调用：{stats.llm_calls} 次</li>
           <li>VLM 调用：{stats.vlm_calls} 次</li>
           <li>缓存命中：{stats.cache_hits} 次</li>
       </ul>
       <h2>成本节省</h2>
       <p>预计节省：{stats._calculate_savings()}%</p>
       </body>
       </html>
       """
       with open(filepath, 'w', encoding='utf-8') as f:
           f.write(html)
   ```

**预留接口（为 PR22 日志系统）**：
```python
def get_export_history(self):
    """获取导出历史"""
    pass

def schedule_auto_export(self, interval_hours):
    """定时自动导出"""
    pass
```

**测试方式**：
- 点击导出按钮
- 确认生成了 JSON、CSV、HTML 三个文件
- 打开文件确认数据正确

**影响范围**：
- `utils/logger.py`（导出逻辑）
- `ui/main_window.py`（导出按钮）

---

### PR21：性能监控面板

**标题**：`[监控优化] 实现性能监控与实时诊断`

**功能描述**：
实时监控系统性能指标（响应时间、内存占用、GPU 利用率等），显示在新的监控面板，帮助诊断瓶颈。

**实现思路**：
1. 在 `utils/logger.py` 中新增性能监控
   ```python
   import time
   import psutil
   
   class PerformanceMonitor:
       def __init__(self):
           self.request_times = []  # 记录每次请求的耗时
           self.start_time = None
       
       def start_request(self):
           """请求开始"""
           self.start_time = time.time()
       
       def end_request(self):
           """请求结束，记录耗时"""
           elapsed = time.time() - self.start_time
           self.request_times.append(elapsed)
       
       def get_metrics(self):
           """获取性能指标"""
           if not self.request_times:
               return {}
           
           return {
               "avg_latency": sum(self.request_times) / len(self.request_times),
               "max_latency": max(self.request_times),
               "min_latency": min(self.request_times),
               "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,  # MB
               "cpu_percent": psutil.Process().cpu_percent(interval=1),
               "total_requests": len(self.request_times)
           }
   ```

2. 在 `ui/main_window.py` 中新增性能面板
   ```python
   self.perf_label = QLabel()
   self.perf_label.setStyleSheet("background: #f0f0f0; padding: 8px;")
   
   self.perf_timer = QTimer(self)
   self.perf_timer.timeout.connect(self._update_performance)
   self.perf_timer.start(1000)  # 每秒更新
   
   def _update_performance(self):
       """更新性能指标"""
       metrics = perf_monitor.get_metrics()
       text = f"""
       性能监控:
       平均响应时间: {metrics.get('avg_latency', 0):.2f}s
       最大响应时间: {metrics.get('max_latency', 0):.2f}s
       内存占用: {metrics.get('memory_usage', 0):.1f} MB
       CPU 使用率: {metrics.get('cpu_percent', 0):.1f}%
       总请求数: {metrics.get('total_requests', 0)}
       """
       self.perf_label.setText(text)
   ```

3. 性能瓶颈诊断
   ```python
   def diagnose_bottleneck(self):
       """诊断性能瓶颈"""
       metrics = perf_monitor.get_metrics()
       
       if metrics['avg_latency'] > 5:
           return "瓶颈：API 调用缓慢，建议检查网络或增加缓存"
       elif metrics['memory_usage'] > 500:
           return "瓶颈：内存占用过高，建议清理缓存"
       elif metrics['cpu_percent'] > 80:
           return "瓶颈：CPU 占用过高，建议降低处理频率"
       else:
           return "系统运行正常"
   ```

**预留接口（为 PR22 日志系统）**：
```python
def get_performance_history(self):
    """获取性能历史数据"""
    pass

def export_performance_report(self):
    """导出性能报告"""
    pass
```

**测试方式**：
- 进行 5+ 轮对话
- 观察性能面板数据更新
- 检查诊断信息是否合理

**影响范围**：
- `utils/logger.py`（性能监控）
- `ui/main_window.py`（性能面板）
- `core/pipeline.py`（埋点）

---

### PR22：日志系统与诊断工具

**标题**：`[运维支持] 实现完整日志系统与诊断工具`

**功能描述**：
集中管理所有系统日志、事件日志、性能日志，提供完整的诊断工具，支持问题追踪和性能分析。

**实现思路**：
1. 在 `utils/logger.py` 中新增日志系统
   ```python
   import logging
   from logging.handlers import RotatingFileHandler
   
   class SystemLogger:
       def __init__(self):
           # 创建日志记录器
           self.logger = logging.getLogger('vda')
           self.logger.setLevel(logging.DEBUG)
           
           # 文件处理器（每个文件最大 10MB，保留 5 个备份）
           handler = RotatingFileHandler(
               'vda.log',
               maxBytes=10*1024*1024,
               backupCount=5
           )
           formatter = logging.Formatter(
               '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
           )
           handler.setFormatter(formatter)
           self.logger.addHandler(handler)
       
       def log_event(self, event_type, details):
           """记录事件"""
           self.logger.info(f"[{event_type}] {details}")
       
       def log_error(self, error_msg):
           """记录错误"""
           self.logger.error(error_msg)
       
       def log_performance(self, operation, duration):
           """记录性能数据"""
           self.logger.debug(f"[PERF] {operation}: {duration:.2f}s")
   
   # 各类日志事件
   def log_asr_event(text, success):
       logger.log_event("ASR", f"{'SUCCESS' if success else 'FAIL'}: {text}")
   
   def log_model_call(model_name, input_tokens, output_tokens):
       logger.log_event("MODEL_CALL", f"{model_name}: in={input_tokens}, out={output_tokens}")
   
   def log_cache_hit(cache_type):
       logger.log_event("CACHE_HIT", f"{cache_type}")
   ```

2. 在 `ui/main_window.py` 中新增诊断工具
   ```python
   self.diagnostic_btn = QPushButton("系统诊断")
   self.diagnostic_btn.clicked.connect(self._run_diagnostic)
   
   def _run_diagnostic(self):
       """运行系统诊断"""
       issues = []
       
       # 检查各服务
       if not ASRClient()._api_key:
           issues.append("❌ ASR 未配置")
       else:
           issues.append("✓ ASR 已配置")
       
       if not LLMClient()._api_key:
           issues.append("❌ LLM 未配置")
       else:
           issues.append("✓ LLM 已配置")
       
       # 检查性能
       perf = perf_monitor.get_metrics()
       if perf['avg_latency'] > 5:
           issues.append(f"⚠ 平均响应时间过长: {perf['avg_latency']:.2f}s")
       
       # 显示诊断结果
       diagnostic_text = "\n".join(issues)
       self.status_label.setText(f"诊断结果:\n{diagnostic_text}")
   ```

3. 日志分析与查询
   ```python
   def analyze_logs(self, start_time, end_time):
       """分析指定时间段的日志"""
       # 统计 ASR 成功率
       # 统计 API 调用次数
       # 统计平均响应时间
       pass
   
   def search_logs(self, keyword):
       """搜索日志"""
       # 返回包含关键词的所有日志行
       pass
   ```

**测试方式**：
- 进行若干操作
- 运行系统诊断，确认检测正确
- 查看 vda.log 文件，确认日志记录完整

**影响范围**：
- `utils/logger.py`（日志系统）
- `ui/main_window.py`（诊断工具）
- 各模块（埋点调用）

---

## 四、第四批 PR 的预留接口清单

### 第三批 PR 需要预留的位置

**在 `utils/logger.py` 中**：
```python
# PR17 需要
def get_tts_config(self):
def set_tts_config(self, speed, volume):

# PR18 需要
def record_model_choice(self, question_type, model_name):

# PR20 需要
def export_to_file(self, filename, format="json"):

# PR21 需要
def get_performance_metrics(self):
```

**在 `core/router.py` 中**：
```python
# PR18 需要
def add_preference(self, question_type, preferred_model):
def get_preference(self, question_type):
```

**在 `ui/main_window.py` 中**：
```python
# PR17 需要
def setup_tts_control_panel(self):

# PR19 需要
def setup_preference_settings(self):

# PR21 需要
def setup_performance_panel(self):
```

---

## 五、第四批 PR 完成后的能力

| 能力 | 模块 |
|------|------|
| 录音、识别、对话、播报 | 第一、二批 |
| 成本优化与缓存 | 第三批 |
| TTS 打断与语速调节 | PR17 |
| 用户偏好学习 | PR18 |
| 动态参数自适应 | PR19 |
| 数据导出与报告 | PR20 |
| 性能监控诊断 | PR21 |
| 完整日志系统 | PR22 |
| **整体评价** | **专业级系统** |

---

## 六、验收标准

### PR17
- ✅ 调节速度滑块，TTS 速度改变
- ✅ 按空格成功打断播放

### PR18
- ✅ 系统学习用户偏好
- ✅ 路由策略根据偏好调整

### PR19
- ✅ 参数面板可调
- ✅ 性能差时自动调优

### PR20
- ✅ 生成 JSON/CSV/HTML 报告
- ✅ 数据准确完整

### PR21
- ✅ 性能面板实时更新
- ✅ 诊断信息合理

### PR22
- ✅ 日志记录完整
- ✅ 诊断工具工作正常

