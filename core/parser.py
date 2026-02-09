"""
HTML parser for extracting media resources from web pages.

Implements intelligent extraction strategies prioritizing video,
then images, then text content.
"""

import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from .models import Resource, ResourceType
from utils.logger import setup_logger


logger = setup_logger(__name__)


class PageParser:
    """
    Web page parser with intelligent media extraction.
    
    Extraction priority:
    1. Video elements (<video>, <source>, .m3u8 links)
    2. Image elements (<img>, <picture>)
    3. Main text content
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize parser with HTTP session.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.ua = UserAgent()
        
        # Default headers
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def parse(self, url: str) -> List[Resource]:
        """
        Parse URL and extract all media resources.
        
        Args:
            url: Target URL to parse
        
        Returns:
            List of extracted Resource objects
        
        Raises:
            requests.RequestException: If HTTP request fails
        """
        logger.info(f"Parsing URL: {url}")
        
        # Fetch page content
        response = self._fetch_page(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'lxml')
        base_url = response.url  # Handle redirects
        
        resources = []
        
        # Priority 1: Extract videos
        resources.extend(self._extract_videos(soup, base_url))
        
        # Priority 2: Extract images
        resources.extend(self._extract_images(soup, base_url))
        
        # Priority 3: Extract text (optional)
        # resources.extend(self._extract_text(soup))
        
        logger.info(f"Extracted {len(resources)} resources from {url}")
        return resources
    
    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        """
        Fetch page content with error handling.
        
        Args:
            url: URL to fetch
        
        Returns:
            Response object or None if failed
        """
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def _extract_videos(self, soup: BeautifulSoup, base_url: str) -> List[Resource]:
        """Extract video resources from HTML."""
        resources = []
        
        # Extract <video> and <source> tags
        for tag in soup.find_all(['video', 'source']):
            src = tag.get('src') or tag.get('data-src')
            if src:
                absolute_url = urljoin(base_url, src)
                resources.append(Resource(
                    url=absolute_url,
                    title=tag.get('title') or tag.get('alt', ''),
                    referer=base_url
                ))
        
        # Extract M3U8 links from <a> tags and scripts
        m3u8_pattern = re.compile(r'https?://[^\s"\'>]+\.m3u8[^\s"\']*', re.IGNORECASE)
        
        # Search in links
        for link in soup.find_all('a', href=True):
            if '.m3u8' in link['href'].lower():
                absolute_url = urljoin(base_url, link['href'])
                resources.append(Resource(
                    url=absolute_url,
                    resource_type=ResourceType.M3U8,
                    title=link.get_text(strip=True) or link.get('title', ''),
                    referer=base_url
                ))
        
        # Search in scripts
        for script in soup.find_all('script'):
            if script.string:
                matches = m3u8_pattern.findall(script.string)
                for match in matches:
                    resources.append(Resource(
                        url=match,
                        resource_type=ResourceType.M3U8,
                        referer=base_url
                    ))
        
        # Deduplicate by URL
        seen = set()
        unique_resources = []
        for res in resources:
            if res.url not in seen:
                seen.add(res.url)
                unique_resources.append(res)
        
        logger.debug(f"Extracted {len(unique_resources)} video resources")
        return unique_resources
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Resource]:
        """Extract image resources from HTML."""
        resources = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src:
                continue
            
            absolute_url = urljoin(base_url, src)
            
            # Skip tiny images (likely icons)
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    if int(width) < 100 or int(height) < 100:
                        continue
                except ValueError:
                    pass
            
            resources.append(Resource(
                url=absolute_url,
                resource_type=ResourceType.IMAGE,
                title=img.get('alt') or img.get('title', ''),
                referer=base_url
            ))
        
        logger.debug(f"Extracted {len(resources)} image resources")
        return resources
    
    def _extract_text(self, soup: BeautifulSoup) -> List[Resource]:
        """Extract main text content (optional feature)."""
        # Extract text from main content areas
        main_tags = soup.find_all(['article', 'main', 'div'], class_=re.compile(r'content|article|post', re.I))
        
        if not main_tags:
            return []
        
        text_content = '\n\n'.join(tag.get_text(strip=True, separator='\n') for tag in main_tags)
        
        if len(text_content) < 100:
            return []
        
        return [Resource(
            url='',
            resource_type=ResourceType.TEXT,
            title='Page Text Content',
            file_extension='.txt',
        )]
