"""
Internationalization (i18n) support for the Crawler application.

Provides translations for Chinese and English with runtime language switching.
"""

from typing import Dict


class I18n:
    """
    Internationalization manager.
    
    Supports runtime language switching between Chinese and English.
    """
    
    LANGUAGES = {
        'en': 'English',
        'zh': '中文'
    }
    
    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        # Application
        'app_title': {
            'en': 'Crawler - Production Web Scraper',
            'zh': 'Crawler - 生产级网页爬虫'
        },
        
        # Main window header
        'header_title': {
            'en': '🌐 Web Resource Crawler',
            'zh': '🌐 网页资源爬虫'
        },
        
        # URL Section
        'url_section_title': {
            'en': 'Step 1: Analyze URL',
            'zh': '步骤 1：分析网址'
        },
        'url_placeholder': {
            'en': 'Enter URL to analyze (e.g., https://example.com/video-page)',
            'zh': '输入要分析的网址（例如：https://example.com/video-page）'
        },
        'analyze_button': {
            'en': '🔍 Analyze',
            'zh': '🔍 分析'
        },
        
        # Resource List
        'resources_title': {
            'en': '📦 Discovered Resources',
            'zh': '📦 发现的资源'
        },
        'select_all': {
            'en': 'Select All',
            'zh': '全选'
        },
        
        # Download Section
        'download_section_title': {
            'en': 'Step 2: Download Selected Resources',
            'zh': '步骤 2：下载选中的资源'
        },
        'download_button': {
            'en': '⬇️ Download',
            'zh': '⬇️ 下载'
        },
        'pause_button': {
            'en': '⏸️ Pause',
            'zh': '⏸️ 暂停'
        },
        'resume_button': {
            'en': '▶️ Resume',
            'zh': '▶️ 恢复'
        },
        'cancel_button': {
            'en': '⏹️ Cancel',
            'zh': '⏹️ 取消'
        },
        'choose_dir_button': {
            'en': '📁 Choose Output Dir',
            'zh': '📁 选择输出目录'
        },
        
        # Progress Section
        'progress_title': {
            'en': 'Progress',
            'zh': '进度'
        },
        'progress_ready': {
            'en': 'Ready',
            'zh': '就绪'
        },
        'progress_analyzing': {
            'en': 'Analyzing...',
            'zh': '分析中...'
        },
        'progress_downloading': {
            'en': 'Downloading: {0}',
            'zh': '下载中：{0}'
        },
        'progress_complete': {
            'en': 'Analysis complete',
            'zh': '分析完成'
        },
        'progress_status': {
            'en': 'Progress: {0}/{1} completed',
            'zh': '进度：已完成 {0}/{1}'
        },
        'progress_all_done': {
            'en': 'All tasks completed',
            'zh': '全部任务完成'
        },
        
        # Activity Log
        'log_title': {
            'en': '📋 Activity Log',
            'zh': '📋 活动日志'
        },
        
        # Status messages
        'status_ready': {
            'en': 'Ready',
            'zh': '就绪'
        },
        'status_analyzing': {
            'en': 'Analyzing URL...',
            'zh': '正在分析网址...'
        },
        'status_error': {
            'en': 'Error occurred',
            'zh': '发生错误'
        },
        
        # Log messages
        'log_ffmpeg_detected': {
            'en': '✓ FFmpeg detected: {0}',
            'zh': '✓ 检测到 FFmpeg：{0}'
        },
        'log_ffmpeg_warning': {
            'en': '⚠️ FFmpeg warning: {0}',
            'zh': '⚠️ FFmpeg 警告：{0}'
        },
        'log_ffmpeg_required': {
            'en': 'M3U8 downloads will not work without FFmpeg',
            'zh': 'M3U8 下载需要 FFmpeg 才能正常工作'
        },
        'log_analyzing_url': {
            'en': 'Analyzing URL: {0}',
            'zh': '正在分析网址：{0}'
        },
        'log_resources_found': {
            'en': 'Found {0} resources',
            'zh': '发现了 {0} 个资源'
        },
        'log_output_dir': {
            'en': 'Output directory: {0}',
            'zh': '输出目录：{0}'
        },
        'log_starting_download': {
            'en': 'Starting download of {0} resource(s)...',
            'zh': '开始下载 {0} 个资源...'
        },
        'log_downloads_complete': {
            'en': 'Downloads completed: {0}/{1}',
            'zh': '下载完成：{0}/{1}'
        },
        'log_cancelled': {
            'en': 'Download cancelled by user',
            'zh': '用户取消了下载'
        },
        'log_paused': {
            'en': 'Downloads paused',
            'zh': '下载已暂停'
        },
        'log_resumed': {
            'en': 'Downloads resumed',
            'zh': '下载已恢复'
        },
        'log_cancelling': {
            'en': 'Cancelling operation...',
            'zh': '正在取消操作...'
        },
        'log_all_complete': {
            'en': '✓ All tasks completed successfully',
            'zh': '✓ 所有任务已成功完成'
        },
        
        # Dialog messages
        'dialog_input_error': {
            'en': 'Input Error',
            'zh': '输入错误'
        },
        'dialog_enter_url': {
            'en': 'Please enter a URL to analyze',
            'zh': '请输入要分析的网址'
        },
        'dialog_invalid_url': {
            'en': 'URL must start with http:// or https://',
            'zh': '网址必须以 http:// 或 https:// 开头'
        },
        'dialog_selection_error': {
            'en': 'Selection Error',
            'zh': '选择错误'
        },
        'dialog_select_resources': {
            'en': 'Please select at least one resource to download',
            'zh': '请至少选择一个要下载的资源'
        },
        'dialog_error': {
            'en': 'Error',
            'zh': '错误'
        },
        'dialog_success': {
            'en': 'Success',
            'zh': '成功'
        },
        'dialog_downloads_complete': {
            'en': 'Downloads completed!\n\nFiles saved to: {0}',
            'zh': '下载完成！\n\n文件保存到：{0}'
        },
        'dialog_select_output_dir': {
            'en': 'Select Output Directory',
            'zh': '选择输出目录'
        },
        
        # Language menu
        'menu_language': {
            'en': 'Language',
            'zh': '语言'
        },
    }
    
    def __init__(self, language: str = 'en'):
        """
        Initialize i18n manager.
        
        Args:
            language: Language code ('en' or 'zh')
        """
        self.current_language = language if language in self.LANGUAGES else 'en'
    
    def get(self, key: str, *args) -> str:
        """
        Get translated string.
        
        Args:
            key: Translation key
            *args: Format arguments
        
        Returns:
            Translated and formatted string
        """
        translation = self.TRANSLATIONS.get(key, {})
        text = translation.get(self.current_language, key)
        
        # Format with arguments if provided
        if args:
            try:
                return text.format(*args)
            except (IndexError, KeyError):
                return text
        
        return text
    
    def set_language(self, language: str) -> None:
        """
        Change current language.
        
        Args:
            language: Language code ('en' or 'zh')
        """
        if language in self.LANGUAGES:
            self.current_language = language
    
    def get_current_language(self) -> str:
        """Get current language code."""
        return self.current_language
    
    def get_language_name(self, language: str = None) -> str:
        """
        Get language display name.
        
        Args:
            language: Language code (uses current if None)
        
        Returns:
            Language display name
        """
        lang = language or self.current_language
        return self.LANGUAGES.get(lang, 'English')


# Global instance
_i18n = I18n()


def get_i18n() -> I18n:
    """Get global i18n instance."""
    return _i18n


def t(key: str, *args) -> str:
    """
    Shorthand for translation.
    
    Args:
        key: Translation key
        *args: Format arguments
    
    Returns:
        Translated string
    """
    return _i18n.get(key, *args)
