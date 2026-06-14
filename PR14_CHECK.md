# 第三批 PR 拆分计划 - 实现对比

## 实现情况统计

| PR | 功能名称 | 计划内容 | 实现状态 | 备注 |
|---|---|---|---|---|
| PR11 | 画面变化检测 | 利用帧差法检测画面变化 | ✅ 已实现 | `core/vision.py` 中 `motion_detect()` 和 `detect_frame_change()` 已完整实现 |
| PR12 | 视觉缓存机制 | 画面未变时复用 VLM 结果 | ❌ 未实现 | `ui/main_window.py` 中没有 `_last_vision_result` 缓存逻辑 |
| PR13 | 上下文摘要压缩 | 老对话自动摘要压缩 | ✅ 已实现 | `core/context.py` 中 `_auto_summarize()` 已实现，触发于超出 max_rounds 时 |
| PR14 | 请求缓存与复用 | 相同问题复用 LLM/VLM 结果 | ✅ 已实现 | `core/router.py` 中 `RequestCache` 类已完整实现，支持 TTL 过期 |
| PR15 | 成本统计面板 | 实时显示 API 调用统计 | ✅ 已实现 | `utils/logger.py` 中 `CostStats` 类已完整实现，`ui/main_window.py` 中集成统计面板 |
| PR16 | UI 布局优化 | 使用 QSplitter 优化布局 | ❌ 未实现 | 当前仍为纯 VBox 布局，未使用 QSplitter |

---

## 详细分析

### ✅ 已实现功能

#### 1. PR11：画面变化检测（✅ 完成）
**位置**：`core/vision.py`
- `motion_detect(prev_frame, curr_frame)` - 调用帧差法检测
- `detect_frame_change(prev_frame, curr_frame, threshold=0.12)` - 基于像素差异占比判断

**缺陷**：在 `ui/main_window.py` 的 `_Worker.run()` 中没有调用 `motion_detect()` 来决定是否上传新图像

#### 2. PR13：上下文摘要压缩（✅ 完成）
**位置**：`core/context.py`
- `_auto_summarize()` - 当历史超出 max_rounds 时触发
- `_simple_summarize(text)` - 简单摘要（截取前 100 字符）
- `get_summary_count()` - 返回摘要次数

**效果**：多轮对话自动压缩老消息，降低 Token 消耗

#### 3. PR14：请求缓存（✅ 完成）
**位置**：`core/router.py`
- `RequestCache` 类 - 支持 TTL 过期的缓存机制
- `get_key()` - 基于问题文本和上下文哈希生成缓存 key
- `get()` / `set()` / `clear()` - 缓存操作

**缺陷**：在 `_Worker.run()` 中没有使用 RequestCache 来复用结果

#### 4. PR15：成本统计面板（✅ 完成）
**位置**：`utils/logger.py` + `ui/main_window.py`
- `CostStats` 类 - 记录 LLM/VLM 调用、缓存命中
- `get_summary()` - 返回统计数据和成本节省百分比
- `_update_stats()` - UI 定时更新统计面板

**效果**：实时展示 API 调用次数、缓存命中率、成本节省百分比

---

### ❌ 未实现功能

#### 1. PR12：视觉缓存机制（❌ 缺失）
**计划内容**：
- 在 `_Worker.run()` 中判断画面是否变化
- 如果画面未变，复用 `_last_vision_result` 而非调用新 VLM
- 记录视觉缓存命中次数

**缺陷**：完全未实现，导致即使画面不变也会重复调用 VLM

#### 2. PR16：UI 布局优化（❌ 缺失）
**计划内容**：
- 使用 QSplitter 分离摄像头和对话区
- 左侧 40% 摄像头、右侧 60% 对话 + 统计
- 新增模式切换按钮

**当前状态**：纯 VBox 垂直布局，无法调整各区域大小

---

## 建议修复顺序

1. **PR12 视觉缓存** - 补充缺失功能（关键）
2. **PR16 UI 优化** - 改进用户体验（可选）

需要继续吗？
