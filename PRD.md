# Role & Context
你是一位拥有 10+ 年经验的 Python 系统架构师及知名开源项目维护者。你擅长构建高内聚、低耦合的桌面应用，你的代码风格严格遵循 PEP 8，且在该领域以“代码如诗”、“架构整洁”著称。

你现在的任务是：从零设计并实现一个名为 **Crawler** 的桌面工具。

# Project Goal
这不是一个简单的脚本，而是一个 **Production-Ready** 的开源项目基石。
目标：
1.  **开箱即用**：用户下载即运行，无复杂的环境依赖地狱。
2.  **可扩展架构**：核心逻辑与 UI 完全解耦，未来无需重构即可接入 Plugins 或 Playwright。
3.  **鲁棒性**：网络波动、FFmpeg 缺失、解析失败均有优雅的降级处理。

---

# Technical Constraints (Strict)

## 1. Core Stack
- **Language**: Python 3.10+ (必须使用 Type Hints)
- **GUI Framework**: PyQt6 (强制)
- **Networking**: `requests` (Session管理), `fake-useragent`
- **Parsing**: `BeautifulSoup4`
- **Media**: 系统级 `ffmpeg` (通过 `subprocess` 调用，禁止 Python 实现流合并)

## 2. Concurrency Model
- **Strict Separation**: UI 线程仅负责渲染。
- **Worker**: 必须继承自 `QThread`。
- **Communication**: 仅通过 `pyqtSignal` 通信，禁止跨线程直接调用方法。
- **Control**: 支持任务的 **暂停** 与 **取消** (is_interrupted 标志位检查)。

## 3. Architecture Pattern (MVC-ish)
- **View (UI)**: 布局使用 `QVBoxLayout`/`QGridLayout`，严禁绝对定位。
- **Controller (Logic)**: 负责调度爬虫、处理信号、更新 UI 状态。
- **Model (Domain)**: 定义 `Resource` 数据类 (dataclass)，而非散乱的 dict。

---

# Implementation Requirements

## A. Feature Specifications
1.  **Input**: URL 输入框 + "Analyze" 按钮。
2.  **Smart Parsing**: 
    - 使用 `requests` 获取 HTML。
    - 智能提取策略：优先提取 `<video>`, `<source>`, `m3u8` 链接；其次提取 `<img>`；最后提取主要文本。
3.  **Dashboard**:
    - 资源列表（带 Checkbox）。
    - 实时日志窗口（QTextEdit，只读）。
    - 进度条（从 分析 -> 下载 -> 合并）。
4.  **Utilities**:
    - `FFmpegCheck`: 启动时检查环境，若无 FFmpeg 则弹窗警告。
    - `Sanitizer`: 文件名非法字符清洗。

## B. Code Quality Standards
- **Type Hinting**: 所有函数参数和返回值必须有类型标注 (e.g., `def parse(url: str) -> List[Resource]:`)。
- **Error Handling**: 使用 `try-except` 块包裹所有 IO 操作，错误信息需通过 Signal 发回 UI，**绝对禁止** 程序崩溃。
- **Project Structure**: 代码必须模块化，不要全部写在一个 `main.py` 中。

---

# Output Deliverables (按顺序输出)

## 1. File Structure Tree
展示清晰的项目目录树，例如 `app/`, `core/`, `ui/`, `utils/`。

## 2. Complete Source Code
请按模块提供完整代码。**注意：**
- 使用 `dataclasses` 定义资源对象。
- 提供 `requirements.txt`。
- 代码中需包含简明扼要的 docstring。
- **CrawlerWorker** 必须包含针对 `m3u8` 的特殊处理逻辑（检测 -> 下载分片 -> ffmpeg 合并）。

## 3. Professional README.md
一份高标准的开源文档，包含：
- **Badges**: (License, Python Version, Build Status).
- **Features**: 核心功能点。
- **Architecture**: 简述 Thread + Signal 的设计模式。
- **Quick Start**: 针对小白用户的运行指南。
- **Troubleshooting**: 常见问题 (403 Forbidden, FFmpeg not found)。

---

# Critical Instructions
- **不要** 写伪代码，必须是可运行的逻辑。
- **不要** 做过度简化的 Demo，要写出你会提交到 GitHub 主分支的代码。
- 重点展示你对 **PyQt6 信号槽机制** 的深刻理解，以及对 **多线程资源竞争** 的规避。