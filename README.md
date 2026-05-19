# AI 视觉处理工具集

AI 视觉处理一站式工具集合，涵盖图片/视频标注、AI 标签生成、ComfyUI 工作流自动化、媒体批量处理、TTS 语音合成等功能。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

---

## 目录

- [快速开始](#快速开始)
- [统一启动器](#统一启动器)
- [核心模块详解](#核心模块详解)
  - [图片打标器](#图片打标器-pictures_mark_tool)
  - [视频打标器](#视频打标器-video_mark_tool)
  - [图像视频标签预览器](#图像视频标签预览器-其他图像视频标签预览)
  - [图片视频过滤工具](#图片视频过滤工具-其他文件处理)
  - [配对工具](#配对工具-其他文件处理配对工具)
  - [文件夹通用处理](#文件夹通用处理-其他文件处理)
  - [图片裁剪工具](#图片裁剪工具-其他图片缩放)
  - [图片缩放工具](#图片缩放工具-其他图片缩放)
- [ComfyUI 工具集](#comfyui-工具集-其他comfyui)
- [格式转换工具](#格式转换工具-其他格式转换)
- [TTS 语音合成](#tts-语音合成-其他tts)
- [其他命令行工具](#其他命令行工具)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [技术栈](#技术栈)

---

## 快速开始

### 环境要求

- **操作系统**: Windows 10/11
- **Python**: 3.11+
- **包管理器**: uv (推荐) 或 pip

### 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install flask websocket-client requests
# 完整依赖见 pyproject.toml
```

### 一键启动

```bash
# Windows — 双击批处理文件
启动工具集.bat                 # 统一工具集启动器

# 或命令行启动
python toolkit_launcher.py     # 统一工具集界面
```

### AI 功能依赖（可选）

AI 标签生成功能需要 OpenAI 兼容 API 服务（如 Ollama、LM Studio、vLLM 等本地部署），配置 API 地址后即可使用。

---

## 统一启动器

`toolkit_launcher.py` — Tkinter 统一工具集界面，将所有带 GUI 的工具按分类组织为卡片式布局。

### 工具分类（5 大类，共 15+ 工具）

| 分类 | 工具 |
|------|------|
| 图片打标 | 图片打标器、词频统计工具 |
| 视频打标 | 视频打标器 |
| 文件处理 | 标签管理器、文件夹通用处理、配对工具、数据集标签提取 |
| 格式转换 | 图片转视频、通用格式转换器、音乐文件重命名 |
| ComfyUI | 动漫转写实、真人转动漫、插帧、提示词提取、视频超分放大 |

**界面特性**: 深色主题、卡片式布局（图标+名称+描述+启动按钮）、悬停高亮效果、可滚动浏览。每个工具通过 `subprocess.Popen` 在独立进程中启动，支持配置独立的 Python 解释器和虚拟环境。

---

## 核心模块详解

### 图片打标器 (pictures_mark_tool)

基于 **PyQt5** 的专业图片标注工具，支持文件夹拖拽导入、AI 自动标签生成、标签频率统计。

**主入口**: `pictures_mark_tool/main.py`

#### 架构概览

| 文件 | 职责 |
|------|------|
| `tagger_ui.py` | 主窗口 TaggerUI(QMainWindow)，3 个 Tab（主界面/词频统计/模型配置），3 面板 Splitter 布局，明暗主题切换 |
| `image_processor.py` | ImageProcessor(QObject)，缩略图缓存（带"未打标"QPainter 叠加层），ThreadPoolExecutor(max_workers=24)，watchdog 文件监控，自动 JPG→PNG 转换 |
| `styles.py` | QPushButton 样式（普通/悬停/按下/重要/导航），LIGHT_THEME / DARK_THEME QSS 字符串 |
| `code/ai_caption_generator.py` | AI 标签生成（OpenAI 兼容 API → Ollama），最多 10 次重试，过滤词检查，生成长度验证（<10 字重试，>max_length 重试+截断），base64 图片编码（max 1024×1024） |
| `code/ollama_caption_generator.py` | 独立版 AI 标签生成器，最多 5 次重试 |
| `code/settings_ui.py` | SettingsUI(QWidget)，4 组配置（API/Model/Advanced/Saved），48 个预设模型名，5 个预设服务，自动检测服务端模型列表，连接测试 |
| `code/statistics.py` | 标签频率统计（QTreeWidget 三列），已打标/未打标文件计数 |
| `code/file_operations.py` | 导入文件夹（QFileDialog）、追加导入（重名自动处理）、导出重命名（前缀+起始编号+打乱选项）、删除选中图片（永久删除+"不再提示"复选框） |
| `code/tag_management.py` | 逗号/分号分隔标签拆分，批量添加/移动/删除/修改标签 |
| `code/preset_tags.py` | 预设标签网格布局（2 列），QTimer 自动关闭弹窗（1 秒） |
| `code/shuffle_files.py` | 三阶段重命名（原名→临时→最终），支持回滚，QProgressDialog 进度 |
| `code/batch_operations.py` | 全选/清空选择批量操作 |

#### 配置文件 (`pictures_mark_tool/code/config.ini`)

```ini
[OLLAMA]           # Ollama 本地服务
api_base_url = http://127.0.0.1:1234/v1
model_name = qwen/qwen3.5-27b
max_tokens = 60000

[VLLM]             # vLLM 服务
api_base_url = http://127.0.0.1:8000/v1
model_name = /models/Qwen3-VL-8B-Instruct

[PROMPTS]          # AI 提示词模板
[FILTER_WORDS]     # 触发重新生成的过滤词
[MAX_CAPTION_LENGTH]  # 最大标签长度限制
```

#### 辅助工具

- **词频统计** (`pictures_mark_tool/tool/词频统计/词频统计.py`) — Tkinter 界面，PanedWindow 布局，词频 Counter 统计，搜索/替换/删除标签，AI 标签重新生成（关键词过滤+短标签过滤），base64 Ollama 集成
- **视频转图片** (`pictures_mark_tool/tool/视频转图片.py`) — CLI 工具，OpenCV 逐帧提取，支持文件夹批量+单文件模式，可配置每秒提取帧数，中文路径编码处理，tqdm 进度条

---

### 视频打标器 (video_mark_tool)

基于 **Tkinter** 的帧级视频标注工具，支持精确到帧的标签标注、AI 描述生成和视频片段导出。

**主入口**: `video_mark_tool/视频打标器/code/video_tagger.py`

#### 架构概览

采用 **"函数导入为类方法"** 模式 — 主类 `VideoTagger` 通过 `from module import func` 将各模块函数导入为实例方法，实现代码分离。

| 模块文件 | 职责 |
|----------|------|
| `video_tagger.py` | 主类 VideoTagger，ttk.PanedWindow 三面板布局（标签预设/视频/控制），config.ini 配置窗口尺寸，video_prompt.txt 外部提示词文件 |
| `video_processing.py` | 视频管理窗口（Toplevel + Listbox），视频添加/加载/列表管理，show_frame（画布自适应 PIL 缩放），play_video（after() 循环），preprocess_frames（线程+进度窗口 / silent 批量模式），resize_to_720p（可配置最长边），save_and_replace_video（临时文件替换模式） |
| `tag_management.py` | 标签 CRUD、排除片段、export_tags（mp4 + txt 双输出，支持 batch_mode 静默导出）、保存/加载标记记录（JSON 含视频元数据）、regenerate_all_tags（线程化重新生成） |
| `ai_features.py` | **LLMClient 类** — 封装 OpenAI 兼容客户端，extract_frames（np.linspace 均匀采样，最多 max_sample_frames 帧），generate_caption（多图输入，`<think>` 标签正则移除 `r"<think>.*?</think>"`，过滤词检查，min_length 验证，最多 10 次重试）。auto_segment_and_recognize（视频列表批量处理+取消支持），generate_ai_caption（单片段→预设标签） |
| `ui_events.py` | 清除/删除/右键菜单事件，字体缩放（±1），进度条拖动（clamp 到 start_frame），窗口大小变化→重绘标记，键盘快捷键（Space/A/D），焦点检测避免输入框冲突 |
| `presets.py` | 两种预设类型：手动（纯文本）和 AI 生成（带缩略图），create_preset_item / create_manual_preset_item，show_full_image（Toplevel 循环播放），show_manual_preset_window（编辑/使用/填充/删除/保存） |
| `utils.py` | draw_tag_markers（进度条 Canvas 彩色片段标记、红色排除区域、起止标记、时间标签），highlight_tag_for_current_frame，is_child_of 控件遍历 |
| `config_window.py` | ConfigWindow 可滚动配置编辑器，6 个配置分组 + video_prompt.txt 外部编辑器（15 行 Text 控件），行级 INI 编辑（保留注释），鼠标滚轮滚动绑定 |

#### 操作流程

1. **加载视频** → 打开视频管理器，支持添加单个文件/文件夹，列表双击加载
2. **帧预处理** → 按目标帧率采样（默认降至 16fps），最长边缩放至 720px
3. **标记片段** → 空格键播放/暂停，A/D 键设置起止帧，输入标签文本后添加标记
4. **AI 标签** → 选中片段→AI 生成标签预设，可选择应用到当前片段
5. **导出** → 导出 mp4 片段+对应 txt 标签文件，或保存/加载 JSON 标记记录

#### 配置文件 (`video_mark_tool/视频打标器/code/config.ini`)

```ini
[MODEL]
api_base_url = http://192.168.13.6:1234/v1
model_name = qwen/qwen3.5-27b
max_new_tokens = 30000
temperature = 0.3

[PROCESSING]
target_max_edge = 720    # 预处理帧最长边
max_sample_frames = 30   # AI 采样最大帧数
target_frame_rate = 16   # 目标帧率
segment_duration = 5     # 自动分段时长(秒)
image_max_size = 720     # 发送给 AI 的图像最大边长

[FILTER_WORDS]           # 含以下词汇时触发重新生成
words = 不符合，公序良俗，低俗，违规，blurry,low resolution,watermark,...
```

**AI 提示词**存储在独立文件 `video_prompt.txt`（与 video_tagger.py 同目录），可通过配置窗口编辑。

#### 附加工具

- **通用拆分视频** (`video_mark_tool/拆分视频工具/通用拆分视频.py`) — CLI 工具，ffmpeg `-c copy` 快速无损分割
- **批量修改帧率** (`video_mark_tool/批量修改帧率.py`) — CLI 工具，ffmpeg `-vf fps=target_fps` 批量修改

---

### 图像视频标签预览器 (其他/图像视频标签预览)

基于 **PyQt5 Mixin 模式**的媒体标签预览工具，支持图片和视频的预览及标签文件管理。

**主入口**: `其他/图像视频标签预览/pic_video_label_manager.py`

#### 架构（Mixin 多继承）

```
VideoLabelManager(QMainWindow, UIComponentsMixin, MediaHandlerMixin,
                  VideoControllerMixin, LabelManagerMixin)
```

| Mixin | 职责 |
|-------|------|
| `UIComponentsMixin` | 界面布局（默认两列/竖屏三列），根据媒体宽高比自动切换布局（aspect_ratio < 0.8 触发竖屏），拖拽提示标签 |
| `MediaHandlerMixin` | 递归加载媒体文件（支持图片+视频），删除当前文件+关联标签（双击确认机制），上下导航自动保存 |
| `VideoControllerMixin` | 视频播放（QTimer 帧更新，BGR→RGB 转换），进度条拖拽跳转，暂停/播放切换，**动画 WebP 完整支持**（帧提取、平均帧率计算、循环播放） |
| `LabelManagerMixin` | 标签文件查找（.txt/.xml/.json/.csv），自动创建/保存标签，修改状态指示（● 未保存 / ✓ 已保存） |
| `utils.py` | get_image_info / get_video_info（分辨率+帧率+总帧数），find_label_file / delete_label_file |

**特色功能**: 动画 WebP 完整播放支持（帧提取→QImage 转换→QTimer 循环），媒体宽高比自适应布局切换。

---

### 图片视频过滤工具 (其他/文件处理)

**`图片视频标签过滤ui.py`** — PyQt5 深色主题三面板过滤器，源文件夹/目标文件夹双列表对比，支持图片+视频预览。

| 功能 | 描述 |
|------|------|
| 源文件夹管理 | 缩略图列表（图片+视频封面），ThumbnailGenerator(QThread) 异步缩略图生成 |
| 目标文件夹管理 | 复制/删除操作，自动关联同名 txt 文件 |
| 视频播放 | 内嵌播放器（播放/暂停/进度条/时间显示），BGR→RGB QImage 转换 |
| 拖拽支持 | 根据鼠标位置自动识别拖拽到左/中/右面板 |
| 删除确认 | 双击删除机制（1 秒内双击确认） |

---

### 配对工具 (其他/文件处理/配对工具)

基于 **Tkinter + tkinterdnd2** 的双面板图片配对工具，支持拖拽导入、智能配对、多种导出模式。

**主入口**: `其他/文件处理/配对工具/main.py`

#### 架构

| 文件 | 职责 |
|------|------|
| `gui.py` | ImagePairToolGUI 主窗口，三列布局（左面板/控制区/右面板），auto_pair_all（ThreadPoolExecutor），export_pairs（尺寸/填充/裁剪/重命名/打乱/旋转增强），Backspace 智能删除（2 次按压），Tab 全屏切换 |
| `panel.py` | ImagePanel 类，Canvas 图片显示+拖拽+滚轮缩放（10%-500%），ThreadPoolExecutor 预加载缓存（前后各 1 张），列表配对高亮（不同后缀名自动匹配 stem） |
| `utils.py` | fill_image_with_background（居中填充白色背景），crop_to_square（1:1 裁剪，支持 top/bottom），generate_renamed_filename（pair_001 格式） |
| `config.py` | 深色模式配色常量，图片扩展名列表，窗口默认尺寸 |

#### 导出功能

- **尺寸模式**: 原始尺寸 / 填充到正方形（居中+白色背景）
- **裁剪模式**: 1:1 裁剪（竖图上/下对齐，横图居中）
- **旋转增强**: 0°/90°/180°/270° 数据增广
- **文件命名**: 保留原名 / 重命名为 pair_001 格式
- **打乱导出**: 随机顺序输出
- **标签保留**: 同步复制同名 TXT 标签文件

---

### 文件夹通用处理 (其他/文件处理)

**`文件夹通用处理_GUI.py`** — PyQt5 文件夹批处理工具，4 个功能 Tab。

| Tab | 功能 |
|-----|------|
| 拆分 | 按文件数量拆分为多个子文件夹 |
| 展平 | 递归将所有子文件夹文件移到根目录 |
| 打乱 | 随机重命名（三阶段重命名防冲突） |
| 提取 | 按扩展名提取文件到目标文件夹 |

ProcessingWorker(QThread) + 进度信号，保留文件名配对关系（如 image_001.jpg ↔ image_001.txt 始终在同一子文件夹）。

---

### 图片裁剪工具 (其他/图片缩放)

**`image_cropper.py`** — PyQt5 图片裁剪工具，按比例裁剪并导出。

| 功能 | 描述 |
|------|------|
| 预设比例 | 1:1, 4:3, 3:4, 16:9, 9:16, 3:2, 2:3, 5:4, 4:5, 21:9, 9:21 + 原始比例 |
| 裁剪位置 | 居中/偏上/偏下/偏左/偏右 |
| 预览 | 带裁剪框叠加层（九宫格辅助线+暗化区域），PreviewLabel(QPainter) 自定义绘制 |
| 键盘快捷键 | 方向键选位置，空格居中，W/Q/E/S 切换图片 |
| 批量导出 | CropWorker(QThread) 多线程处理，JPEG quality 可调（50-100），自动避免文件名冲突 |
| 拖拽导入 | DropFrame 拖拽区域，支持文件夹拖放 |

---

### 图片缩放工具 (其他/图片缩放)

**`image_resizer.py`** — PyQt5 图片压缩工具，将图片批量压缩到目标文件大小以下。

| 功能 | 描述 |
|------|------|
| 压缩算法 | JPEG: 二分搜索 quality（10-100），quality≤15 时自动缩小尺寸。PNG: 二分搜索 compress_level（1-9）。WebP: quality 二分搜索 + method=2 |
| 输出选项 | 覆盖原图 / 输出到指定目录 |
| 进度反馈 | ImageResizeWorker(QThread)，实时逐文件结果列表（✓ 成功 / ⏭ 跳过 / ✗ 失败） |
| 拖拽导入 | DropLineEdit 拖拽区域，自动识别文件夹 |

---

## ComfyUI 工具集 (其他/comfyui)

基于 Tkinter 的 ComfyUI 工作流批量处理工具，通过 HTTP API 与 ComfyUI 服务通信。

### 批量动漫转写实 (`batch_anime2real.py`)

~1000 行 Tkinter GUI，双 Canvas 预览（输入右对齐/输出左对齐），支持完整/半自动模式。

- **LoRA 管理**: 从 `J:\models\loras` 自动发现 LoRA 模型
- **提示词预设**: JSON 文件保存/加载提示词预设
- **半自动模式**: 每张图片处理前弹出确认对话框，支持跳过/接受/参数调整
- **处理控制**: 暂停/恢复/停止，F11 全屏，Tab 隐藏控制面板
- **输出组织**: 自动分 control/target 子文件夹

### 真人转动漫 (`真人转动漫.py`)

与 batch_anime2real 类似架构但针对不同 LoRA 节点（node 297），简化版半自动对话框。

### 其他 ComfyUI 工具

| 工具 | 功能 |
|------|------|
| `batch_image_upscale.py` | SeedVR2 模型视频超分辨率，可配置 seed/max_resolution/min_resolution/longer_edge，VAE/DiT 模型路径 |
| `插帧.py` | 视频插帧批量处理，递归文件发现 |
| `wan22放大.py` | Wan2.2 视频放大工作流，CLI/Tkinter 双模式 |
| `提示词提取.py` | 从 PNG metadata（`Image.info["prompt"]`→node 113）和视频 ffprobe metadata（comment→workflow.nodes）提取提示词 |

> **注意**: `其他/comfyui/web_ui/` 目录下的 Streamlit Web UI 文件未在本次文件读取范围内，其功能以实际代码为准。

---

## 格式转换工具 (其他/格式转换)

| 工具 | 框架 | 功能 |
|------|------|------|
| `图片转视频.py` | Tkinter | 单张图片→单帧 MP4，支持中文路径（np.fromfile + cv2.imdecode） |
| `transform.py` | Tkinter | 通用媒体转换器，4 种转换类型（图片/视频/音频/全部），ffmpeg + OpenCV GIF 回退，GIF 帧率/分辨率可调，ThreadPoolExecutor(4) 帧处理 |
| `music_kmg.py` | CLI | 批量 `.kgm.flac` → `.kgm` 文件重命名 |

---

## TTS 语音合成 (其他/tts)

基于 Gradio 本地服务的 TTS 文本转语音方案，提供 OpenAI API 兼容层。

| 文件 | 功能 |
|------|------|
| `qwen3tts/gradio的tts.py` | Gradio Client 调用本地 TTS 服务（localhost:7862），支持多种音色（少女音/御姐/萝莉/老男人），winsound 播放 |
| `qwen3tts/tts_adapter.py` | TTSAAdapter 封装类，`generate_tts(text, voice, speed, temperature)` 统一接口 |
| `qwen3tts/tts_server.py` | **FastAPI 服务**，提供 OpenAI 兼容的 `/v1/audio/speech` 端点，voice 映射（alloy→少女音等），StreamingResponse 流式输出，支持 mp3/wav/flac/opus |
| `qwen3tts/test_openai_client.py` | 使用 `openai` SDK 的 `client.audio.speech.create()` 调用本地 TTS 服务的示例（需先启动 tts_server.py） |
| `qwen3tts/test.py` | Gradio Client 直接调用测试脚本 |

---

## 其他命令行工具

| 工具 | 功能 |
|------|------|
| `其他/视频扩充/扩充视频时长.py` | OpenCV 读取视频帧，通过帧重复将短视频拉伸到 5 秒（16fps），不足则填充最后一帧 |
| `其他/文件处理/数据集标签提取.py` | Tkinter filedialog 选择源/目标文件夹，递归提取所有 .txt 文件内容合并为一个文件 |
| `其他/文件处理/txt改逗号.py` | Tkinter 选择文件夹，批量将 txt 文件中中文逗号→英文逗号，删除所有空格 |
| `其他/文件处理/批量改文件名.py` | CLI 工具，删除文件名中特定后缀（`_real`, `_fake`, `_hd`, `_sd`） |
| `其他/文件处理/多段音频拼接/audio_merger_gui.py` | Tkinter 音频拼接 GUI，ffprobe 获取时长，ffmpeg concat 合并，支持 mp3/wav/flac/aac/m4a/ogg 输出 |
| `其他/文件处理/多段音频拼接/拼接音频.py` | 简化版（代码为空文件） |

---

## 配置说明

### 打标器 AI 配置

两个打标器各自使用独立的 `config.ini`，均通过 OpenAI 兼容 API 调用 AI 服务：

| 配置项 | 说明 |
|--------|------|
| `api_base_url` | OpenAI 兼容 API 地址（支持 Ollama/LM Studio/vLLM/DeepSeek/SiliconCloud 等） |
| `api_key` | API 密钥（本地服务通常为 `ollama` 或 `EMPTY`） |
| `model_name` | 模型名称（如 `qwen/qwen3.5-27b`, `qwen3-vl:30b`） |
| `temperature` / `top_p` | 生成参数 |
| `max_new_tokens` / `max_tokens` | 最大生成 token 数 |

### 过滤词机制

AI 生成的标签如果包含 `[FILTER_WORDS]` 中配置的词汇（支持中英文），会自动触发重新生成（最多 10 次），最后仍包含则强制移除过滤词。

### 视频处理参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target_max_edge` | 720 | 预处理帧最长边像素 |
| `target_frame_rate` | 16 | 预处理目标帧率 |
| `max_sample_frames` | 30 | AI 分析时最大采样帧数 |
| `image_max_size` | 720 | 发送给 AI 的图片最大边长 |

---

## 项目结构

```
Ai_visual_processing_tools/
├── toolkit_launcher.py                       # 统一工具集启动器
├── 启动工具集.bat                             # Windows 快捷启动
├── requirements.txt                          # 核心依赖
├── pyproject.toml                            # uv 项目配置
│
├── pictures_mark_tool/                       # 图片打标器（PyQt5）
│   ├── main.py                               # 程序入口
│   ├── tagger_ui.py                          # 主界面（3 Tab, 3 面板）
│   ├── image_processor.py                    # 图片处理+缩略图（ThreadPoolExecutor）
│   ├── styles.py                             # 主题样式（明/暗 QSS）
│   ├── code/
│   │   ├── ai_caption_generator.py           # AI 标签生成（OpenAI→Ollama）
│   │   ├── ollama_caption_generator.py       # 独立版 AI 生成器
│   │   ├── settings_ui.py                    # 模型配置界面
│   │   ├── statistics.py                     # 标签频率统计
│   │   ├── file_operations.py                # 文件导入/导出/删除
│   │   ├── tag_management.py                 # 标签 CRUD
│   │   ├── preset_tags.py                    # 预设标签面板
│   │   ├── shuffle_files.py                  # 三阶段重命名
│   │   ├── batch_operations.py               # 全选/清空
│   │   ├── ui_event_handlers.py              # UI 事件处理
│   │   └── config.ini                        # 配置文件
│   ├── tool/
│   │   ├── 词频统计/词频统计.py                # 标签分析器（Tkinter）
│   │   └── 视频转图片.py                      # 视频帧提取（CLI）
│   └── 启动打标器.bat
│
├── video_mark_tool/                          # 视频打标器（Tkinter）
│   ├── 视频打标器/code/
│   │   ├── video_tagger.py                   # 主程序（PanedWindow 三面板）
│   │   ├── video_processing.py               # 视频加载/播放/帧处理
│   │   ├── video_clipper.py                  # 独立视频裁剪器
│   │   ├── tag_management.py                 # 标签管理+导出
│   │   ├── ai_features.py                    # LLMClient + AI 标签生成
│   │   ├── ui_events.py                      # UI 事件+键盘快捷键
│   │   ├── presets.py                        # 预设标签管理
│   │   ├── utils.py                          # Canvas 标记绘制
│   │   ├── config_window.py                  # 配置编辑窗口
│   │   ├── config.ini                        # 配置文件
│   │   └── video_prompt.txt                  # AI 提示词
│   ├── 拆分视频工具/通用拆分视频.py            # ffmpeg 视频分割
│   └── 批量修改帧率.py                        # ffmpeg 帧率修改
│
├── 其他/
│   ├── comfyui/                              # ComfyUI 批量处理工具
│   │   ├── batch_anime2real.py               # 批量动漫转写实（~1000行）
│   │   ├── 真人转动漫.py                      # 真人转动漫（Tkinter）
│   │   ├── batch_image_upscale.py            # SeedVR2 超分辨率
│   │   ├── 插帧.py                           # 视频插帧
│   │   ├── wan22放大.py                      # Wan2.2 放大
│   │   ├── 提示词提取.py                      # 元数据提示词提取
│   │   └── web_ui/                           # Streamlit Web 应用
│   │
│   ├── 格式转换/                              # 媒体格式转换
│   │   ├── 图片转视频.py                      # 图片→视频（Tkinter）
│   │   ├── transform.py                      # 通用转换器（Tkinter）
│   │   └── music_kmg.py                      # .kgm.flac 重命名
│   │
│   ├── 图片缩放/                              # 图片尺寸处理
│   │   ├── image_cropper.py                  # 比例裁剪工具（PyQt5）
│   │   └── image_resizer.py                  # 压缩到目标大小（PyQt5）
│   │
│   ├── 视频扩充/                              # 视频时长处理
│   │   └── 扩充视频时长.py                    # 帧重复扩展到5秒
│   │
│   ├── 图像视频标签预览/                       # 媒体标签预览器（PyQt5）
│   │   ├── pic_video_label_manager.py        # 主窗口+入口
│   │   ├── ui_components.py                  # UI 组件+布局切换
│   │   ├── media_handler.py                  # 媒体加载/显示/删除
│   │   ├── video_controller.py               # 视频播放+动画WebP
│   │   ├── label_manager.py                  # 标签文件管理
│   │   └── utils.py                          # 辅助函数
│   │
│   ├── 文件处理/                              # 通用文件操作
│   │   ├── 配对工具/                          # 双面板图片配对
│   │   │   ├── main.py                       # 入口
│   │   │   ├── gui.py                        # 主界面（~1080行）
│   │   │   ├── panel.py                      # 单侧图片面板
│   │   │   ├── utils.py                      # 图片处理函数
│   │   │   └── config.py                     # 配色常量
│   │   ├── 文件夹通用处理_GUI.py               # 拆分/展平/打乱/提取
│   │   ├── 图片视频标签过滤ui.py               # 三面板过滤器
│   │   ├── 数据集标签提取.py                    # TXT 内容合并
│   │   ├── 批量改文件名.py                      # 后缀删除
│   │   ├── txt改逗号.py                        # 标点转换
│   │   └── 多段音频拼接/                       # 音频合并
│   │       ├── audio_merger_gui.py            # GUI（Tkinter）
│   │       └── 拼接音频.py
│   │
│   └── tts/qwen3tts/                         # TTS 语音合成
│       ├── gradio的tts.py                     # Gradio Client 调用
│       ├── tts_adapter.py                     # TTS 适配器封装
│       ├── tts_server.py                      # FastAPI OpenAI 兼容服务
│       ├── test_openai_client.py              # OpenAI SDK 调用示例
│       └── test.py                            # 直接调用测试
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **GUI 框架** | PyQt5（图片打标、标签预览、过滤、裁剪、缩放、文件夹处理）、Tkinter（视频打标、配对、ComfyUI 批量、格式转换、音频拼接）、Streamlit（ComfyUI Web UI）、Gradio（TTS） |
| **AI 集成** | OpenAI Python SDK（兼容 Ollama/LM Studio/vLLM/DeepSeek/SiliconCloud），支持视觉语言模型（qwen3-vl, Qwen3.5-27b 等），base64 图片编码 |
| **视频处理** | OpenCV（帧读写、BGR↔RGB 转换、resize）、ffmpeg（subprocess 调用，concat/copy/fps 修改） |
| **图像处理** | Pillow（格式转换、缩放、裁剪、动画 WebP 读取）、QImage/QPixmap（Qt 端渲染） |
| **并发模型** | ThreadPoolExecutor（图片批量 I/O）、threading.Thread + root.after()（不阻塞 UI）、QThread + pyqtSignal（Qt 进度更新） |
| **配置管理** | configparser INI 文件、JSON 预设/标记记录、外部 txt 提示词文件 |
| **包管理** | uv (pyproject.toml) + pip (requirements.txt) |

---

*最后更新: 2026/05/19*
