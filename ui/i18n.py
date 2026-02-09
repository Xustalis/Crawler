
"""
Internationalization support.
"""

from typing import Dict, Any

class I18n:
    def __init__(self):
        self.current_language = 'zh'
        
        self.translations = {
            'en': {
                'app_title': 'Crawler V2.0',
                'header_title': 'Universal Crawler',
                'url_section_title': 'Target URL',
                'url_placeholder': 'Enter URL to crawl (e.g., https://example.com)',
                'analyze_button': 'Analyze',
                'concurrency_title': 'Concurrency',
                'concurrency_label': 'Max Workers: {0}',
                'resources_title': 'Resources',
                'cat_images': 'Images',
                'cat_videos': 'Videos',
                'cat_documents': 'Docs/Audio',
                'btn_details': 'Details',
                'download_button': 'Download Selected',
                'cancel_button': 'Cancel',
                'stop_button': 'Stop',
                'status_ready': 'Ready',
                'status_analyzing': 'Analyzing...',
                'status_error': 'Error occurred',
                'progress_status': 'Progress: {0}/{1}',
                'progress_complete': 'Analysis Complete',
                'progress_all_done': 'All Tasks Finished',
                'menu_language': 'Language',
                'log_title': 'Activity Log',
                'log_analyzing_url': 'Analyzing URL: {0}',
                'log_ffmpeg_detected': 'FFmpeg detected: {0}',
                'log_ffmpeg_warning': 'FFmpeg warning: {0}',
                'log_ffmpeg_required': 'Please install FFmpeg for video merging.',
                'log_starting_download': 'Starting download of {0} files...',
                'log_cancelling': 'Cancelling...',
                'dialog_error': 'Error',
                'dialog_success': 'Success',
                'dialog_selection_error': 'Selection Error',
                'dialog_select_resources': 'Please select at least one resource category.',
                'dialog_downloads_complete': 'All downloads finished.\nSaved to: {0}',
                'dialog_input_error': 'Input Error',
                'dialog_enter_url': 'Please enter a valid URL.',
                'dialog_select_output_dir': 'Select Output Directory',
                
                # New keys
                'tab_new_task': 'New Task',
                'tab_history': 'History',
                'col_id': 'ID',
                'col_url': 'URL',
                'col_status': 'Status',
                'col_progress': 'Progress',
                'col_date': 'Date',
                'col_path': 'Path',
                'col_filename': 'Filename',
                'col_size': 'Size',
                'select_all': 'Select All',
                'btn_confirm': 'Confirm',
                'details_title': 'Details: {0}',
                'view_grid': 'Grid View',
                'view_list': 'List View'
            },
            'zh': {
                'app_title': '通用爬虫 V2.0',
                'header_title': '资源采集器',
                'url_section_title': '目标地址',
                'url_placeholder': '请输入要爬取的网址 (如 https://example.com)',
                'analyze_button': '开始分析',
                'concurrency_title': '并发设置',
                'concurrency_label': '最大线程数: {0}',
                'resources_title': '资源列表',
                'cat_images': '图片资源',
                'cat_videos': '视频资源',
                'cat_documents': '文档/音频',
                'btn_details': '详情',
                'download_button': '下载选中资源',
                'cancel_button': '取消任务',
                'stop_button': '停止',
                'status_ready': '就绪',
                'status_analyzing': '正在分析网页...',
                'status_error': '发生错误',
                'progress_status': '进度: {0}/{1}',
                'progress_complete': '分析完成',
                'progress_all_done': '所有任务已完成',
                'menu_language': '语言 (Language)',
                'log_title': '运行日志',
                'log_analyzing_url': '正在分析 URL: {0}',
                'log_ffmpeg_detected': '检测到 FFmpeg: {0}',
                'log_ffmpeg_warning': 'FFmpeg警告: {0}',
                'log_ffmpeg_required': '请安装FFmpeg以支持视频合并功能。',
                'log_starting_download': '开始下载 {0} 个文件...',
                'log_cancelling': '正在取消...',
                'dialog_error': '错误',
                'dialog_success': '成功',
                'dialog_selection_error': '选择错误',
                'dialog_select_resources': '请至少选择一个资源分类。',
                'dialog_downloads_complete': '所有下载已完成。\n保存位置: {0}',
                'dialog_input_error': '输入错误',
                'dialog_enter_url': '请输入有效的网址。',
                'dialog_select_output_dir': '选择保存目录',
                
                # New keys
                'tab_new_task': '新建任务',
                'tab_history': '历史记录',
                'col_id': 'ID',
                'col_url': '链接',
                'col_status': '状态',
                'col_progress': '进度',
                'col_date': '时间',
                'col_path': '路径',
                'col_filename': '文件名',
                'col_size': '大小',
                'select_all': '全选',
                'btn_confirm': '确认',
                'details_title': '详情: {0}',
                'view_grid': '网格视图',
                'view_list': '列表视图'
            }
        }
    
    def set_language(self, lang: str):
        if lang in self.translations:
            self.current_language = lang
            
    def get(self, key: str, *args) -> str:
        text = self.translations.get(self.current_language, {}).get(key, key)
        if args:
            try:
                return text.format(*args)
            except:
                return text
        return text

# Global instance
_i18n = I18n()

def get_i18n() -> I18n:
    return _i18n

def t(key: str, *args) -> str:
    return _i18n.get(key, *args)
