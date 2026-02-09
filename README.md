# 🌐 Crawler - Production Web Scraper
# 🌐 Crawler - 生产级网页爬虫工具

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English Version

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)
![License](https://img.shields.io/badge/license-GPL%20v3-orange.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

A **production-ready** desktop application for intelligent web resource extraction with advanced M3U8 streaming support. Built with clean architecture principles and strict type safety.

### ✨ Features

- 🧠 **Smart UX**: Intelligent URL normalization (auto-HTTPS) and simplified workflow
- 📊 **Aggregated Results**: Category-based resource counts instead of overwhelming file lists
- 🔍 **Smart Parsing**: Intelligent extraction of videos, images, and M3U8 streams from any web page
- 🎬 **M3U8 Support**: Automatic playlist parsing, segment downloading, and FFmpeg merging
- 📦 **Batch Downloads**: One-click download for entire categories (Images, Videos, etc.)
- ⏸️ **Pause & Resume**: Full control over download operations
- 🌏 **Bilingual UI**: Seamless switching between Chinese and English
- 🎨 **Modern UI**: Cyberpunk-inspired dark theme with responsive layouts
- 🔒 **Robust**: HTTPS->HTTP fallback and comprehensive error handling

### 🚀 Quick Start

#### Prerequisites
1. **Python 3.10+** installed
2. **FFmpeg** installed and added to PATH (for M3U8 support)
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

#### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Xustalis/Crawler.git
cd Crawler

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

### 📂 Project Structure

```
Crawler/
├── app.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── LICENSE                   # GPL v3 License
│
├── core/                     # Business logic layer
│   ├── models.py            # Resource data models
│   ├── parser.py            # HTML parsing engine
│   ├── downloader.py        # Download manager
│   └── m3u8_handler.py      # M3U8 stream handler
│
├── workers/                  # QThread workers
│   ├── signals.py           # Signal definitions
│   └── crawler_worker.py    # Main worker thread
│
├── ui/                       # PyQt6 interface
│   ├── main_window.py       # Main window
│   ├── widgets.py           # Custom widgets
│   ├── styles.py            # QSS stylesheets
│   └── i18n.py              # Internationalization
│
└── utils/                    # Utility functions
    ├── ffmpeg_checker.py    # FFmpeg detection
    ├── sanitizer.py         # Filename cleaning
    └── logger.py            # Logging setup
```

### 🛠️ Troubleshooting

**Issue: "FFmpeg not found"**
- Verify: `ffmpeg -version`
- Install FFmpeg and add to system PATH

**Issue: "403 Forbidden" Error**
- The app uses `fake-useragent` and Referer headers
- Some sites may have advanced anti-scraping measures

### 📝 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

**Note**: GPL v3 is compatible with PyQt6's GPL/Commercial dual licensing.

### 👤 Author

**Xustalis**
- GitHub: [@Xustalis](https://github.com/Xustalis)

### 🙏 Acknowledgments

- **PyQt6**: Powerful GUI framework
- **BeautifulSoup**: HTML parsing
- **FFmpeg**: Video processing

---

<a name="chinese"></a>
## 中文版本

![Python 版本](https://img.shields.io/badge/python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)
![许可证](https://img.shields.io/badge/license-GPL%20v3-orange.svg)
![平台](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

一个**生产级**桌面应用程序，用于智能网页资源提取，支持高级 M3U8 流媒体处理。采用清晰的架构原则和严格的类型安全构建。

### ✨ 功能特性

- 🧠 **智能体验**：智能 URL 归一化（自动补全 HTTPS）和简化的工作流
- 📊 **聚合结果**：基于类别的资源统计，告别眼花缭乱的文件列表
- 🔍 **智能解析**：从任何网页智能提取视频、图片和 M3U8 流
- 🎬 **M3U8 支持**：自动播放列表解析、分段下载和 FFmpeg 合并
- 📦 **批量下载**：一键下载整个类别（图片、视频等）
- ⏸️ **暂停与恢复**：完全控制下载操作
- 🌏 **双语界面**：中英文无缝切换
- 🎨 **现代化界面**：赛博朋克风格暗黑主题，响应式布局
- 🔒 **健壮稳定**：HTTPS->HTTP 自动降级和全面的错误处理

### 🚀 快速开始

#### 前置要求
1. 安装 **Python 3.10+**
2. 安装 **FFmpeg** 并添加到 PATH（M3U8 支持必需）
   - Windows: 从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

#### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Xustalis/Crawler.git
cd Crawler

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行应用
python app.py
```

### 📂 项目结构

```
Crawler/
├── app.py                    # 应用入口
├── requirements.txt          # Python 依赖
├── LICENSE                   # GPL v3 许可证
│
├── core/                     # 核心业务逻辑层
│   ├── models.py            # 资源数据模型
│   ├── parser.py            # HTML 解析引擎
│   ├── downloader.py        # 下载管理器
│   └── m3u8_handler.py      # M3U8 流处理器
│
├── workers/                  # QThread 工作线程
│   ├── signals.py           # 信号定义
│   └── crawler_worker.py    # 主工作线程
│
├── ui/                       # PyQt6 界面层
│   ├── main_window.py       # 主窗口
│   ├── widgets.py           # 自定义组件
│   ├── styles.py            # QSS 样式表
│   └── i18n.py              # 国际化
│
└── utils/                    # 工具函数
    ├── ffmpeg_checker.py    # FFmpeg 检测
    ├── sanitizer.py         # 文件名清理
    └── logger.py            # 日志设置
```

### 🛠️ 故障排除

**问题："FFmpeg not found"**
- 验证：`ffmpeg -version`
- 安装 FFmpeg 并添加到系统 PATH

**问题："403 Forbidden" 错误**
- 应用自动使用 `fake-useragent` 和 Referer 头
- 某些网站可能有高级反爬虫措施

### 📝 许可证

本项目采用 **GNU 通用公共许可证 v3.0** - 详见 [LICENSE](LICENSE) 文件。

**注意**：GPL v3 与 PyQt6 的 GPL/商业双重许可兼容。

### 👤 作者

**Xustalis**
- GitHub: [@Xustalis](https://github.com/Xustalis)

### 🙏 致谢

- **PyQt6**：强大的 GUI 框架
- **BeautifulSoup**：HTML 解析
- **FFmpeg**：视频处理
