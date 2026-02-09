"""
Industrial-grade Network Layer.

Features:
- Session pooling (Keep-Alive)
- Automatic Retries with Exponential Backoff
- Dynamic User-Agent
- Timeout enforcement
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import logging

logger = logging.getLogger(__name__)

# Common User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

class NetworkManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NetworkManager, cls).__new__(cls)
            cls._instance._init_session()
        return cls._instance
    
    def _init_session(self):
        """Initialize requests Session with retry logic."""
        self.session = requests.Session()
        
        # Retry strategy: 3 retries, backoff factor 0.5s (0.5, 1.0, 2.0)
        # Status codes to retry: 500, 502, 503, 504
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default timeout
        self.timeout = 10 
        
        logger.info("NetworkManager initialized with retry strategy")

    def get(self, url: str, **kwargs) -> requests.Response:
        """Robust GET request."""
        # Set default timeout if not provided
        kwargs.setdefault('timeout', self.timeout)
        
        # Rotate User-Agent
        headers = kwargs.get('headers', {})
        if 'User-Agent' not in headers:
            headers['User-Agent'] = random.choice(USER_AGENTS)
        kwargs['headers'] = headers
        
        try:
            return self.session.get(url, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {str(e)}")
            raise

    def close(self):
        self.session.close()
