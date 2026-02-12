"""
URL normalization utilities for the Crawler application.

Provides smart URL handling with:
- Automatic protocol completion (https:// by default)
- HTTPS -> HTTP fallback on SSL errors
- Input sanitization
- Strict validation
"""

from typing import Tuple, Optional
from urllib.parse import urlparse
import re
import socket
import requests
from requests.exceptions import SSLError, ConnectionError, Timeout, RequestException

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Compile regex for basic URL structure validation
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def validate_url(url: str) -> str:
    """
    Validate and normalize a URL. Raises ValueError if invalid.
    
    Args:
        url: Raw user input
        
    Returns:
        Normalized, valid URL
        
    Raises:
        ValueError: If URL is malformed or invalid
    """
    normalized = normalize_url(url)
    if not is_valid_url(normalized):
        raise ValueError(f"Invalid URL format: {url}")
    return normalized


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid using regex and parsing.
    
    Args:
        url: URL string to check
        
    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    if len(url) > 2048: # IE maximum URL length
        return False
        
    try:
        # 1. Regex check
        if not URL_REGEX.match(url):
            return False
            
        # 2. Parse check
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


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
    """
    if not input_str:
        return ""
        
    # Step 1: Strip whitespace
    url = input_str.strip()
    
    # Step 2: Check for protocol presence
    lower_url = url.lower()
    if not lower_url.startswith(('http://', 'https://', 'ftp://')):
        # Default to HTTPS
        url = f"https://{url}"
        logger.debug(f"Auto-completed URL with https: {url}")
    
    return url


def check_connection(url: str, timeout: int = 5) -> bool:
    """
    Check if a URL is reachable by resolving DNS and opening a socket.
    Lighter than a full HTTP request.
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.split(':')[0]
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        socket.create_connection((host, port), timeout=timeout)
        return True
    except OSError:
        return False


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
    # 1. Validate first
    if not is_valid_url(url):
         raise ValueError(f"Invalid URL: {url}")

    if headers is None:
        headers = {}
    
    # Ensure User-Agent
    if 'User-Agent' not in headers:
        import random
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        headers['User-Agent'] = random.choice(user_agents)
    
    # Add common headers
    headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    headers.setdefault('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8')
    headers.setdefault('Accept-Encoding', 'gzip, deflate')
    headers.setdefault('Connection', 'keep-alive')
    
    current_url = url
    
    # Attempt 1 (HTTPS favored)
    try:
        logger.info(f"Attempting request to: {current_url}")
        response = requests.get(current_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response, current_url
        
    except (SSLError, ConnectionError) as e:
        # HTTPS failed, try HTTP fallback
        logger.warning(f"Connection failed ({type(e).__name__}), trying HTTP fallback...")
        
        if current_url.startswith('https://'):
            fallback_url = current_url.replace('https://', 'http://', 1)
            
            try:
                logger.info(f"Fallback request to: {fallback_url}")
                response = requests.get(fallback_url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response, fallback_url
                
            except RequestException as fallback_error:
                logger.error(f"Both HTTPS and HTTP failed for {url}")
                raise RequestException(
                    f"Unable to connect to {url}. Both HTTPS and HTTP failed."
                ) from fallback_error
        else:
            raise
            
    except Timeout:
        logger.error(f"Request timeout for {current_url}")
        raise RequestException(f"Request timed out: {current_url}")
        
    except RequestException as e:
        logger.error(f"Request failed for {current_url}: {e}")
        raise
