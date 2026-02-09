"""
NetworkManager - Advanced HTTP client with anti-scraping features.

V2.0: Implements dynamic UA rotation, proxy support, login with CSRF,
and intelligent retry mechanisms.
"""

import re
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from utils.logger import setup_logger


logger = setup_logger(__name__)


class NetworkManager:
    """
    Advanced HTTP client with anti-scraping features.
    
    Features:
    - Dynamic User-Agent rotation per request
    - HTTP/HTTPS/SOCKS5 proxy support
    - Automatic CSRF token extraction for login
    - Session cookie persistence
    - Intelligent retry with UA rotation on failure
    """
    
    # Common CSRF token field names
    CSRF_FIELD_NAMES = [
        'csrf_token', 'csrfmiddlewaretoken', '_token', 'authenticity_token',
        '_csrf', 'csrf', '__RequestVerificationToken', 'XSRF-TOKEN'
    ]
    
    def __init__(
        self,
        proxy: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
        rotate_ua_per_request: bool = True
    ):
        """
        Initialize NetworkManager.
        
        Args:
            proxy: Proxy URL (http://..., https://..., or socks5://...)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on failure
            rotate_ua_per_request: If True, rotate UA on every request
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.rotate_ua_per_request = rotate_ua_per_request
        self.ua = UserAgent()
        
        # Create session
        self.session = requests.Session()
        
        # Configure proxy if provided
        self._proxy = None
        if proxy:
            self.set_proxy(proxy)
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default headers
        self._update_headers()
    
    def _update_headers(self, rotate_ua: bool = True) -> None:
        """Update session headers, optionally rotating UA."""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if rotate_ua:
            headers['User-Agent'] = self.ua.random
            logger.debug(f"Rotated UA: {headers['User-Agent'][:50]}...")
        
        self.session.headers.update(headers)
    
    def set_proxy(self, proxy: str) -> None:
        """
        Configure proxy for all requests.
        
        Args:
            proxy: Proxy URL (supports http, https, socks5)
                   Example: "http://user:pass@host:port"
                            "socks5://host:port"
        """
        self._proxy = proxy
        
        if proxy.startswith('socks'):
            # SOCKS proxy requires PySocks
            self.session.proxies = {
                'http': proxy,
                'https': proxy,
            }
        else:
            self.session.proxies = {
                'http': proxy,
                'https': proxy,
            }
        
        logger.info(f"Proxy configured: {proxy.split('@')[-1]}")  # Hide credentials
    
    def get(
        self,
        url: str,
        rotate_ua: bool = None,
        referer: str = None,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Perform GET request with anti-scraping features.
        
        Args:
            url: Target URL
            rotate_ua: Override UA rotation setting for this request
            referer: Set custom Referer header
            **kwargs: Additional arguments passed to requests.get()
        
        Returns:
            Response object or None if failed
        """
        should_rotate = rotate_ua if rotate_ua is not None else self.rotate_ua_per_request
        
        if should_rotate:
            self._update_headers(rotate_ua=True)
        
        if referer:
            self.session.headers['Referer'] = referer
        
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            logger.warning(f"Request failed: {url} - {e}")
            
            # Retry with new UA
            if should_rotate and self.max_retries > 0:
                logger.info("Retrying with new User-Agent...")
                self._update_headers(rotate_ua=True)
                try:
                    response = self.session.get(
                        url,
                        timeout=self.timeout,
                        allow_redirects=True,
                        **kwargs
                    )
                    response.raise_for_status()
                    return response
                except requests.RequestException as retry_e:
                    logger.error(f"Retry failed: {retry_e}")
            
            return None
    
    def post(
        self,
        url: str,
        data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        rotate_ua: bool = None,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Perform POST request.
        
        Args:
            url: Target URL
            data: Form data to POST
            json_data: JSON data to POST
            rotate_ua: Override UA rotation setting
            **kwargs: Additional arguments
        
        Returns:
            Response object or None if failed
        """
        should_rotate = rotate_ua if rotate_ua is not None else self.rotate_ua_per_request
        
        if should_rotate:
            self._update_headers(rotate_ua=True)
        
        try:
            response = self.session.post(
                url,
                data=data,
                json=json_data,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            logger.error(f"POST request failed: {url} - {e}")
            return None
    
    def login(
        self,
        login_url: str,
        form_data: Dict[str, str],
        csrf_page_url: str = None
    ) -> bool:
        """
        Perform login with automatic CSRF token handling.
        
        Args:
            login_url: URL to POST login credentials
            form_data: Login form data (username, password, etc.)
            csrf_page_url: URL to fetch CSRF token from (defaults to login_url)
        
        Returns:
            True if login successful
        """
        # Fetch CSRF token
        csrf_url = csrf_page_url or login_url
        csrf_response = self.get(csrf_url, rotate_ua=False)
        
        if not csrf_response:
            logger.error("Failed to fetch CSRF page")
            return False
        
        soup = BeautifulSoup(csrf_response.text, 'lxml')
        csrf_token = self._extract_csrf_token(soup)
        
        if csrf_token:
            # Add token to form data
            token_name = self._find_csrf_field_name(soup)
            form_data[token_name] = csrf_token
            logger.debug(f"CSRF token extracted: {csrf_token[:20]}...")
        
        # Perform login - don't rotate UA to maintain session consistency
        login_response = self.post(login_url, data=form_data, rotate_ua=False)
        
        if login_response and login_response.ok:
            # Check for successful login indicators
            if self._check_login_success(login_response):
                logger.info("Login successful")
                return True
        
        logger.warning("Login may have failed")
        return False
    
    def _extract_csrf_token(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract CSRF token from HTML page."""
        # Check hidden input fields
        for field_name in self.CSRF_FIELD_NAMES:
            # Check by name attribute
            token_input = soup.find('input', {'name': field_name})
            if token_input and token_input.get('value'):
                return token_input['value']
            
            # Check by id attribute
            token_input = soup.find('input', {'id': field_name})
            if token_input and token_input.get('value'):
                return token_input['value']
        
        # Check meta tags
        meta_csrf = soup.find('meta', {'name': re.compile(r'csrf', re.I)})
        if meta_csrf and meta_csrf.get('content'):
            return meta_csrf['content']
        
        return None
    
    def _find_csrf_field_name(self, soup: BeautifulSoup) -> str:
        """Find the actual CSRF field name used in the form."""
        for field_name in self.CSRF_FIELD_NAMES:
            if soup.find('input', {'name': field_name}):
                return field_name
        return 'csrf_token'  # Default fallback
    
    def _check_login_success(self, response: requests.Response) -> bool:
        """Check if login was successful based on response."""
        # Check for error indicators in response
        error_patterns = [
            'invalid', 'incorrect', 'wrong password', 'login failed',
            'authentication failed', 'error', '用户名或密码错误'
        ]
        
        content_lower = response.text.lower()
        for pattern in error_patterns:
            if pattern in content_lower:
                return False
        
        # Assume success if no error indicators found
        return True
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current session cookies."""
        return dict(self.session.cookies)
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Set session cookies."""
        self.session.cookies.update(cookies)
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
