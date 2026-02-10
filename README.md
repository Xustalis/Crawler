# 🕷️ Aegis Crawler / 宙斯盾爬虫

<div align="center">

![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)
![License](https://img.shields.io/badge/license-GPL%20v3-red.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

[English](#english) | [中文 (Chinese)](#chinese)

</div>

---

<a name="english"></a>
## 📖 Introduction

**Aegis Crawler** is an industrial-grade, desktop-based web resource extraction tool designed for high-performance and stability. It features a modern, cyberpunk-inspired UI, intelligent parsing strategies, and a robust concurrency model suitable for heavy-duty scraping tasks.

### ✨ Key Features

- **🚀 Dynamic Concurrency**: Adaptive worker pool that scales based on queue depth and system load.
- **🧠 Smart Parsing**: Heuristic-based content extraction for HTML, JSON, and M3U8 streams.
- **Traffic Optimization**: Intelligent header inspection to skip large binary files during scanning.
- **💾 M3U8 HLS Support**: Native support for HLS streaming, including segment downloading and FFmpeg merging.
- **🛡️ Robustness**: Global exception handling, session pooling, and automatic retries with exponential backoff.
- **🎨 Modern UI**: Responsive PyQt6 interface with dark mode and bilingual support (EN/ZH).

### 🏗️ Architecture Design

The application follows a **Producer-Consumer** pattern with valid clean architecture principles.

```mermaid
graph TD
    UI[User Interface (PyQt6)] -->|Signal: Start/Stop| WP[Worker Pool]
    WP -->|Spawn| RW[Request Workers (Threads)]
    
    subgraph Core Logic
        RW -->|Fetch| NET[Network Manager]
        RW -->|Parse| PAR[Parser Engine]
        PAR -->|Extract| RES[Resources]
    end
    
    subgraph Data Persistence
        RES -->|Store| DB[(SQLite Database)]
        DB -->|WAL Mode| WAL[Write-Ahead Log]
    end
    
    subgraph Download System
        UI -->|Signal: Download| TP[Thread Pool]
        TP -->|Execute| DL[Download Runnable]
        DL -->|Stream| NET
        DL -->|Write| FS[File System]
    end
```

### 🚀 Getting Started

#### Prerequisites
- **Python 3.10+**
- **FFmpeg** (Required for video processing)
  - Windows: [Download](https://ffmpeg.org/download.html)
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`

#### Installation

```bash
# 1. Clone repository
git clone https://github.com/Xustalis/Crawler.git
cd Crawler

# 2. Setup virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python app.py
```

### 🤝 Contribution Guidelines

We welcome contributions! Please follow these steps to ensure a smooth process:

1.  **Fork the Project**: Create your own copy of the repository.
2.  **Create Feature Branch**: `git checkout -b feature/AmazingFeature`
3.  **Commit Changes**: `git commit -m 'feat: Add some AmazingFeature'` - please use [Conventional Commits](https://www.conventionalcommits.org/).
4.  **Push to Branch**: `git push origin feature/AmazingFeature`
5.  **Open Pull Request**: Describe your changes in detail.

**Reporting Issues:**
- Please use the [Issue Tracker](https://github.com/Xustalis/Crawler/issues).
- Include reproduction steps, logs, and screenshots.

---

<a name="chinese"></a>
## 📖 简介 (Introduction)

**宙斯盾爬虫 (Aegis Crawler)** 是一款工业级桌面端网页资源提取工具，专为高性能和稳定性而设计。它拥有现代化的赛博朋克风格界面、智能解析策略以及适合高负载抓取任务的健壮并发模型。

### ✨ 核心特性

- **🚀 动态并发**: 自适应工作线程池，根据队列深度和系统负载自动伸缩。
- **🧠 智能解析**: 基于启发式的 HTML、JSON 和 M3U8 流媒体内容提取。
- **流量优化**: 智能 HTTP 头检查，在扫描阶段自动跳过大型二进制文件，节省带宽。
- **💾 M3U8 HLS 支持**: 原生支持 HLS 流媒体，包括分片下载和 FFmpeg 自动合并。
- **🛡️ 健壮性**: 全局异常处理、会话池管理以及带指数退避的自动重试机制。
- **🎨 现代化 UI**: 响应式 PyQt6 界面，支持暗黑模式和中英双语切换。

### 🏗️ 架构设计

本应用遵循 **生产者-消费者** 模式，采用清晰的分层架构原则。

- **UI 层**: 负责用户交互，通过信号槽机制与业务逻辑解耦。
- **Core 层**: 包含网络请求、HTML 解析、数据库管理等核心业务逻辑。
- **Workers 层**: 包含请求工作线程和下载线程池，负责具体任务执行。

### 🚀 快速开始

#### 前置要求
- **Python 3.10+**
- **FFmpeg** (视频处理必需)
  - Windows: [下载](https://ffmpeg.org/download.html)并添加到 PATH
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`

#### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Xustalis/Crawler.git
cd Crawler

# 2. 创建虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行应用
python app.py
```

### 🤝 贡献指南

我们非常欢迎您的贡献！请遵循以下步骤：

1.  **Fork 项目**: 创建您自己的代码库副本。
2.  **创建特性分支**: `git checkout -b feature/AmazingFeature`
3.  **提交更改**: `git commit -m 'feat: Add some AmazingFeature'` - 请使用规范化提交信息。
4.  **推送到分支**: `git push origin feature/AmazingFeature`
5.  **提交 Pull Request**: 详细描述您的更改。

**反馈问题:**
- 请使用 [Issue Tracker](https://github.com/Xustalis/Crawler/issues)。
- 请务必包含复现步骤、日志文件和截图。

---

### 📜 License

Distributed under the **GPL v3 License**. See `LICENSE` for more information.

> **Project Aegis** - *Secure, Fast, Intelligent.*
