# 第五批 PR 拆分计划（精简版）

## 一、设计理念与风险控制

Avatar 是 AI 的具象化代表，但在**赛事 3 天短周期里，素材工作量是最大瓶颈**。

本计划采用"**20% 工作量拿 80% 效果**"的策略：
- 只保留核心必做功能（4 个状态 + 状态同步）
- 素材用免费现成资源（像素风宠物）
- 可选功能严格控制工作量（简化版交互、2 个关键动作）
- **必须做开关控制**，出问题一键关闭，不影响核心对话功能

---

## 二、状态与素材方案

### 核心 4 个状态

| 状态 | 描述 | 帧数 | 素材来源 |
|------|------|------|---------|
| **IDLE** | 空闲等待 | 3-4 帧 | 免费素材库（如 itch.io） |
| **LISTENING** | 录音中 | 3-4 帧 | 免费素材库 |
| **THINKING** | 处理中 | 3-4 帧 | 免费素材库 |
| **SPEAKING** | 播报中 | 3-4 帧 | 免费素材库 |

**总素材数**: 4 个状态 × 4 帧 = **16 张**（1 套主题）

### 可选功能素材

- **点击问候**: 1 张静态图
- **点头动作**: 4 帧
- **歪头动作**: 4 帧
- **总计**: 9 张

**整个 Avatar 系统素材总数**: 16 + 9 = **25 张**（极低）

---

## 三、第五批 PR 详细规划

### PR23：Avatar 基础系统（精简版）

**标题**：`[交互] 实现 Avatar 基础动画系统`

**功能描述**：
实现 Avatar 动画系统，支持 4 个核心状态切换。使用免费现成素材，代码极简。

**实现思路**：

1. **下载免费素材**
   - 去 itch.io 或 opengameart.org 找免费的像素风宠物 / 机器人 2D 动画素材
   - 下载后裁切成 4 套状态各 4 帧

2. **实现 Avatar 类（极简版）**
   ```python
   # ui/avatar.py
   from PyQt5.QtGui import QPixmap, QTimer
   from PyQt5.QtWidgets import QLabel
   
   class Avatar(QLabel):
       """Avatar 动画角色（精简版）"""
       
       STATES = {
           "idle": 4,
           "listening": 4,
           "thinking": 4,
           "speaking": 4,
       }
       
       def __init__(self):
           super().__init__()
           self.current_state = "idle"
           self.frame_index = 0
           self.frames = {}
           self._load_frames()
           
           # 定时器
           self.timer = QTimer()
           self.timer.timeout.connect(self._next_frame)
       
       def _load_frames(self):
           """加载 4 个状态的帧"""
           for state, count in self.STATES.items():
               self.frames[state] = []
               for i in range(1, count + 1):
                   path = f"assets/avatar/{state}_{i}.png"
                   self.frames[state].append(QPixmap(path))
       
       def set_state(self, state):
           """切换状态"""
           if state != self.current_state:
               self.current_state = state
               self.frame_index = 0
               self.timer.stop()
               self.timer.start(100)  # 100ms 更新一次
       
       def _next_frame(self):
           """播放下一帧"""
           frames = self.frames[self.current_state]
           self.setPixmap(frames[self.frame_index])
           self.frame_index = (self.frame_index + 1) % len(frames)
       
       def disable(self):
           """禁用 Avatar（出问题时关闭）"""
           self.timer.stop()
           self.hide()
   ```

3. **在主窗口集成**
   ```python
   # ui/main_window.py
   from ui.avatar import Avatar
   
   class MainWindow:
       def __init__(self):
           # ...
           self.avatar = Avatar()
           self.avatar.setMinimumSize(150, 150)
           left_layout.addWidget(self.avatar)
           
           # 添加 Avatar 开关（出问题一键关闭）
           self.avatar_toggle = QCheckBox("显示 Avatar")
           self.avatar_toggle.setChecked(True)
           self.avatar_toggle.stateChanged.connect(self._toggle_avatar)
           
           control_layout.addWidget(self.avatar_toggle)
       
       def _toggle_avatar(self, state):
           if state == Qt.Checked:
               self.avatar.show()
           else:
               self.avatar.disable()
   ```

**素材资源**：
- 下载免费素材并裁切到 `assets/avatar/` 目录
- 文件命名：`idle_1.png`, `idle_2.png`, ... `speaking_4.png`

**测试方式**：
- 各状态帧应正确加载并循环播放
- Avatar 开关应能隐藏 / 显示

**工作量**：
- 代码：30 分钟
- 素材处理：30 分钟
- **总计：1 小时**

---

### PR24：系统状态同步

**标题**：`[交互] Avatar 与系统状态绑定`

**功能描述**：
Avatar 状态与系统当前状态自动同步：录音 → listening，处理 → thinking，播报 → speaking，空闲 → idle。

**实现思路**：

1. **在 core/pipeline.py 中添加状态回调**
   ```python
   class AppPipeline:
       def __init__(self):
           # ...
           self.on_avatar_state = None
       
       def set_avatar_state(self, state):
           if self.on_avatar_state:
               self.on_avatar_state(state)
       
       def process_audio(self, audio_path):
           try:
               self.set_avatar_state("thinking")
               # ... ASR/LLM/VLM ...
               self.set_avatar_state("speaking")
               return text, reply, tts_path
           except:
               self.set_avatar_state("idle")
               return "", "", ""
   ```

2. **在 main_window.py 中连接**
   ```python
   class MainWindow:
       def __init__(self):
           # ...
           self.pipeline.on_avatar_state = self.avatar.set_state
       
       def _start_recording(self):
           if self.audio.start():
               self.avatar.set_state("listening")
               self.record_btn.setText("停止并发送")
       
       def _on_done(self, user_text, reply, tts_path):
           # ...
           if reply:
               self.avatar.set_state("speaking")
           else:
               self.avatar.set_state("idle")
   ```

**测试方式**：
- 录音时 Avatar 显示 listening
- 处理时显示 thinking
- 播报时显示 speaking
- 完成后回到 idle

**工作量**：
- 代码：20 分钟
- **总计：20 分钟**

---

## 第二档：可选扩展 PR

### PR25：简化版交互（优先级 ⭐⭐⭐）

**标题**：`[交互] Avatar 点击交互与简化版口型同步`

**功能描述**：
- 用户点击 Avatar 弹出一句问候语
- TTS 播报时 Avatar 嘴巴固定频率张合（简化版，不做实时音频分析）

**实现思路**：

1. **点击交互**
   ```python
   # ui/avatar.py
   class Avatar(QLabel):
       def mousePressEvent(self, event):
           """点击 Avatar"""
           if self.current_state == "idle":
               # 弹出提示
               msg = QMessageBox(self.parent())
               msg.setText("👋 你好！我是你的 AI 助手。\n有什么可以帮你的吗？")
               msg.setWindowTitle("Avatar")
               msg.exec_()
   ```

2. **简化版口型同步**
   ```python
   # 播报时，固定频率张合嘴巴（不用实时音频分析）
   def sync_mouth_simple(self, duration_seconds):
       """播报期间，固定频率张合嘴巴"""
       # 嘴巴张：0.3秒，闭：0.3秒
       intervals = int(duration_seconds / 0.6)
       for i in range(intervals):
           # 切换到张嘴帧
           self.setPixmap(self.frames["speaking"][(i * 2) % 4])
           QApplication.processEvents()
           time.sleep(0.3)
           # 切换到闭嘴帧
           self.setPixmap(self.frames["speaking"][(i * 2 + 1) % 4])
           QApplication.processEvents()
           time.sleep(0.3)
   ```

3. **在 main_window.py 中调用**
   ```python
   def _on_done(self, user_text, reply, tts_path):
       if tts_path:
           # 获取 TTS 音频时长
           import wave
           with wave.open(tts_path, 'rb') as wav:
               duration = wav.getnframes() / wav.getframerate()
           
           # 播放并同步嘴巴
           self.avatar.sync_mouth_simple(duration)
           os.startfile(tts_path)
   ```

**工作量**：
- 代码：20 分钟
- **总计：20 分钟**

**演示效果**：
- 点击 Avatar 有互动感
- 播报时嘴巴动作虽然简化，但视觉上足够自然

---

### PR26：2 个关键反馈动作（优先级 ⭐⭐）

**标题**：`[交互] Avatar 成功/失败反馈动作`

**功能描述**：
成功识别 → Avatar 点头，识别失败 → Avatar 歪头。只做这 2 个关键动作，素材极少。

**实现思路**：

1. **加载 2 个动作**
   ```python
   class Avatar(QLabel):
       def __init__(self):
           # ...
           self.actions = {
               "nod": [],      # 点头：4 帧
               "confused": []  # 歪头：4 帧
           }
           self._load_actions()
       
       def _load_actions(self):
           """加载 2 个动作"""
           for action in ["nod", "confused"]:
               for i in range(1, 5):
                   path = f"assets/avatar/{action}_{i}.png"
                   self.actions[action].append(QPixmap(path))
   ```

2. **播放动作**
   ```python
   def play_action(self, action_name, then_state="idle"):
       """播放一个动作，然后回到指定状态"""
       frames = self.actions[action_name]
       for frame in frames:
           self.setPixmap(frame)
           QApplication.processEvents()
           time.sleep(0.1)  # 100ms 每帧
       self.set_state(then_state)
   ```

3. **在对话完成时触发**
   ```python
   def _on_done(self, user_text, reply, tts_path):
       if reply and len(reply) > 10:
           # 成功回复，播放点头
           self.avatar.play_action("nod", then_state="speaking")
       else:
           # 失败，播放歪头
           self.avatar.play_action("confused", then_state="idle")
   ```

**素材需求**：
- 点头动作：4 帧
- 歪头动作：4 帧
- **总计：8 张**

**工作量**：
- 代码：15 分钟
- 素材处理：15 分钟（制作或下载）
- **总计：30 分钟**

**演示效果**：
- 反馈感很强，用户能清晰感受到 Avatar 在"回应"
- 虽然只有 2 个动作，但足以覆盖大多数场景

---

## 四、执行建议与时间分配

### 第一档：必做（2-3 小时，必须完成）

| PR | 时间 | 备注 |
|---|---|---|
| PR23 | 1 小时 | 下载素材 + 写代码 |
| PR24 | 20 分钟 | 状态绑定 |
| **小计** | **1.3 小时** | **核心效果已实现** |

### 第二档：可选扩展（1-1.5 小时，时间充裕再做）

| PR | 时间 | 优先级 | 备注 |
|---|---|---|---|
| PR25 | 40 分钟 | ⭐⭐⭐ | 点击 + 简化口型 |
| PR26 | 30 分钟 | ⭐⭐ | 2 个反馈动作 |
| **小计** | **1 小时** | | 按优先级做 |

---

## 五、风险控制清单

- ✅ **必须做开关控制**：Avatar 出问题一键关闭，不影响核心对话
- ✅ **不追求完美**：用免费现成素材，不自制，省时间
- ✅ **代码极简**：没有复杂的实时分析，避免调试坑
- ✅ **逐步推进**：PR23 + PR24 完成后，核心价值已实现，PR25/26 是锦上添花
- ✅ **演示稳定**：充分测试，确保 Avatar 不会导致主链路卡顿

---

## 六、赛事价值定位

### 答辩亮点
"我们不止步于功能实现，而是进一步考虑用户交互体验。通过 Avatar 将抽象的系统状态具象化，用拟人化的表情和动作降低用户认知成本，让对话更有温度。"

### 演示效果
- 系统状态可视化：用户能清晰看到系统在做什么
- 交互反馈强：用户的每次提问都能得到 Avatar 的反馈
- 简洁高效：核心逻辑极简，不会成为系统瓶颈

### 保险底线
如果 Avatar 在演示时出现问题，一键禁用，不影响核心对话功能的演示。

---

## 七、总体工作量对比

| 方案 | PR 数 | 代码工作量 | 素材工作量 | 调试风险 | 建议 |
|---|---|---|---|---|---|
| 原计划（6 PR） | 6 | 中 | **极高**（千张+） | 高 | ❌ 不适合赛事 |
| 精简版（4 PR） | 4 | 极低 | **极低**（25 张） | 低 | ✅ **推荐** |

---

## 八、时间表示例（3 天赛事）

### Day 1
- 完成 PR23 + PR24（1.3 小时）
- 核心 Avatar 系统上线，演示可用

### Day 2
- 完成 PR25 + PR26（1 小时，可选）
- 交互和反馈动作完善

### Day 3
- 测试、调试、打磨
- 充分验证 Avatar 与核心功能的兼容性

---

## 对标总结

这个精简版 Avatar 方案以**最小工作量拿最大演示效果**为目标：

✅ 代码极简（极少调试坑）  
✅ 素材极少（25 张图，用现成资源）  
✅ 风险极低（有开关，出问题可关闭）  
✅ 效果很强（状态可视化 + 反馈动作）  
✅ 赛事适配（3 天能完成）  

**强烈建议采用这个方案，而不是原计划的 6 PR 全套实现。**

