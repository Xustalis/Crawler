"""
URL normalization utilities for the Crawler application.

Provides smart URL handling with:
- Automatic protocol completion (https:// by default)
- HTTPS -> HTTP fallback on SSL errors
- Input sanitization
"""

from typing import Tuple
from urllib.parse import urlparse
import requests
from requests.exceptions import SSLError, ConnectionError, Timeout, RequestException

from utils.logger import setup_logger

logger = setup_logger(__name__)


def normalize_url(input_str: str) -> str:
    """
    Normalize user input into a valid URL.
    
    1. Strips whitespace
    2. Adds https:// if no protocol specified
    3. Returns normalized URL ready for request
    
    Args:
        input_str: Raw user input (e.g., "google.com", "https://example.com")
    
    Returns:
        Normalized URL with protocol (e.g., "https://google.com")
    
    Example:
        >>> normalize_url("  google.com  ")
        "https://google.com"
        >>> normalize_url("http://example.com")
        "http://example.com"
    """
    # Step 1: Strip whitespace
    url = input_str.strip()
    
    if not url:
        return ""
    
    # Step 2: Check for protocol presence
    # 用户可能输入 "google.com" 或 "www.google.com"
    lower_url = url.lower()
    if not lower_url.startswith(('http://', 'https://')):
        # 默认补全 HTTPS 协议
        url = f"https://{url}"
        logger.debug(f"Auto-completed URL with https: {url}")
    
    return url


def fetch_with_fallback(
    url: str,
    headers: dict = None,
    timeout: int = 15
) -> Tuple[requests.Response, str]:
    """
    Fetch URL with automatic HTTPS -> HTTP fallback.
    
    Tries HTTPS first, falls back to HTTP on SSL/Connection errors.
    
    Args:
        url: Normalized URL (should already have protocol)
        headers: Optional request headers
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (Response object, final_url used)
    
    Raises:
        RequestException: If both HTTPS and HTTP attempts fail
    """
    if headers is None:
        headers = {}
    
    # 确保有 User-Agent - 使用更真实的浏览器标识
    if 'User-Agent' not in headers:
        # 多个真实 User-Agent 轮换
        import random
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        headers['User-Agent'] = random.choice(user_agents)
    
    # 添加常见浏览器头
    headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    headers.setdefault('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8')
    headers.setdefault('Accept-Encoding', 'gzip, deflate')
    headers.setdefault('Connection', 'keep-alive')
    
    current_url = url
    
    # 第一次尝试（通常是 HTTPS）
    try:
        logger.info(f"Attempting request to: {current_url}")
        response = requests.get(current_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response, current_url
        
    except (SSLError, ConnectionError) as e:
        # HTTPS 失败，尝试降级到 HTTP
        logger.warning(f"HTTPS failed ({type(e).__name__}), trying HTTP fallback...")
        
        if current_url.startswith('https://'):
            # 降级到 HTTP
            fallback_url = current_url.replace('https://', 'http://', 1)
            
            try:
                logger.info(f"Fallback request to: {fallback_url}")
                response = requests.get(fallback_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response, fallback_url
                
            except RequestException as fallback_error:
                # HTTP 也失败了，抛出原始错误
                logger.error(f"Both HTTPS and HTTP failed for {url}")
                raise RequestException(
                    f"无法连接到 {url}。HTTPS 和 HTTP 均失败。"
                ) from fallback_error
        else:
            # 原本就是 HTTP，直接失败
            raise
            
    except Timeout:
        logger.error(f"Request timeout for {current_url}")
        raise RequestException(f"请求超时：{current_url}")
        
    except RequestException as e:
        logger.error(f"Request failed for {current_url}: {e}")
        raise
