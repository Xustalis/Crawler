"""
HTML parser for extracting media resources from web pages.

V2.0: Implements universal parsing strategy including:
- MIME detection for JSON/Text responses
- Deep text extraction (articles, quotes)
- Pagination discovery
- Script data sniffing
"""

import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import Resource, ResourceType
from .network import NetworkManager
from utils.logger import setup_logger


logger = setup_logger(__name__)


class PageParser:
    """
    Web page parser with intelligent media and text extraction.
    
    Strategies:
    1. Content-Type detection (JSON vs HTML)
    2. Video/Image extraction
    3. Structural text extraction (Article, Quotes, Tables)
    4. Pagination discovery
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize parser with NetworkManager.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.network = NetworkManager(timeout=timeout)
    
    def parse(self, url: str) -> tuple[List[Resource], List[str]]:
        """
        Parse URL and extract all resources using intelligent strategies.
        
        Args:
            url: Target URL to parse
        
        Returns:
            Tuple of (extracted resources, pagination links)
        """
        logger.info(f"Parsing URL: {url}")
        
        # Fetch page content
        response = self.network.get(url)
        if not response:
            return [], []
        
        # Strategy 1: MIME Detection
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'application/json' in content_type:
            return self._parse_json_response(response), []
        
        # Default to HTML parsing
        return self._parse_html_response(response)

    def _parse_json_response(self, response: requests.Response) -> List[Resource]:
        """Parse JSON response into a text resource."""
        try:
            data = response.json()
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            
            return [Resource(
                url=response.url,
                resource_type=ResourceType.JSON_DATA,
                title="API Response",
                file_extension=".json",
                content=formatted_json,
                metadata={'status_code': response.status_code}
            )]
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return []

    def _parse_html_response(self, response: requests.Response) -> tuple[List[Resource], List[str]]:
        """Parse HTML response for videos, images, and text."""
        soup = BeautifulSoup(response.text, 'lxml')
        base_url = response.url
        resources = []
        
        # V3.0: Smart content extraction - only parse main content area
        main_content_soup = self._extract_main_content(soup)
        
        # Extract Media from main content
        resources.extend(self._extract_videos(main_content_soup, base_url))
        resources.extend(self._extract_images(main_content_soup, base_url))
        
        # Extract Text (structured content)
        resources.extend(self._extract_text_content(main_content_soup, base_url))
        
        # Check for JSON in <script> tags
        resources.extend(self._sniff_script_json(soup))
        
        # Discover pagination links (use original soup for nav)
        pagination_links = self.get_pagination_links(soup, base_url)
        
        logger.info(f"Extracted {len(resources)} resources and {len(pagination_links)} links from {response.url}")
        
        return resources, pagination_links
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Public API for extracting navigation links (Pagination + Depth).
        """
        return self.get_pagination_links(soup, base_url)
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Extract main content area using heuristic scoring.
        
        Filters out sidebars, footers, ads, and nav elements to focus
        on the primary content.
        
        Args:
            soup: Full page soup
            
        Returns:
            Soup of highest-scoring content block (or original if scoring fails)
        """
        # Find all potential content containers
        candidates = soup.find_all(['div', 'article', 'section', 'main'])
        
        if not candidates:
            return soup  # Fallback to full page
        
        best_block = soup
        best_score = -1000
        
        for block in candidates:
            score = self._score_content_block(block)
            
            if score > best_score:
                best_score = score
                best_block = block
        
        # If best score is still negative, use full page
        if best_score < 0:
            return soup
        
        # Return a new soup from the best block's HTML
        return BeautifulSoup(str(best_block), 'lxml')
    
    def _score_content_block(self, block) -> int:
        """
        Score a content block for importance.
        
        Positive signals: headers, paragraphs, large images, 'content' classes
        Negative signals: 'sidebar', 'footer', 'nav', 'ads' classes
        
        Args:
            block: BeautifulSoup Tag element
            
        Returns:
            Integer score (higher = more likely to be main content)
        """
        score = 0
        
        # Check class names
        classes = ' '.join(block.get('class', [])).lower()
        
        # Positive signals in class names
        positive_keywords = ['content', 'article', 'main', 'post', 'entry', 'text', 'body']
        for keyword in positive_keywords:
            if keyword in classes:
                score += 10
        
        # Negative signals in class names
        negative_keywords = ['sidebar', 'footer', 'nav', 'menu', 'ads', 'ad', 'comment', 'aside', 'widget']
        for keyword in negative_keywords:
            if keyword in classes:
                score -= 20
        
        # Count content indicators
        h1_count = len(block.find_all('h1'))
        h2_count = len(block.find_all('h2'))
        p_count = len(block.find_all('p'))
        img_count = len(block.find_all('img'))
        
        score += h1_count * 10
        score += h2_count * 5
        score += p_count * 2
        score += img_count * 3
        
        # Penalize blocks with very little text
        text_length = len(block.get_text(strip=True))
        if text_length < 50:
            score -= 10
        elif text_length > 500:
            score += 15
        
        return score
    
    def get_pagination_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract pagination links (next page).
        
        Call this from the Worker to get next URLs.
        """
        links = []
        
        # 1. Standard rel="next"
        tag = soup.find('a', rel='next')
        if tag and tag.get('href'):
            links.append(urljoin(base_url, tag['href']))
            
        # 2. Class based (e.g. .next > a, or a.next)
        for cls in ['next', 'pagination-next', 'nav-next']:
            # Search for element with this class
            elements = soup.find_all(class_=cls)
            for el in elements:
                # If element is <a>
                if el.name == 'a' and el.get('href'):
                    links.append(urljoin(base_url, el['href']))
                # If element contains <a> (e.g. li.next > a)
                else:
                    a_tag = el.find('a', href=True)
                    if a_tag:
                        links.append(urljoin(base_url, a_tag['href']))

        # 3. Text based (fuzzy match)
        # We process all <a> tags and check their text content
        # This is safer than using string=re.compile because of mixed content
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True).lower()
            if any(k in text for k in ['next page', 'next >', '下一页', 'older posts']):
                # Avoid "Next extraction", "Next steps" false positives?
                # Usually pagination links are short.
                if len(text) < 20: 
                    links.append(urljoin(base_url, a['href']))
                    
            # Specific check for simple "Next" often accompanied by arrows
            if text == 'next' or text.startswith('next '):
                 links.append(urljoin(base_url, a['href']))
        
        return list(set(links))  # Deduplicate

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
        
        # Extract M3U8 links from <a> tags
        for link in soup.find_all('a', href=True):
            if '.m3u8' in link['href'].lower():
                absolute_url = urljoin(base_url, link['href'])
                resources.append(Resource(
                    url=absolute_url,
                    resource_type=ResourceType.M3U8,
                    title=link.get_text(strip=True) or link.get('title', ''),
                    referer=base_url
                ))
        
        # Look for M3U8 in strings (simple regex)
        # Note: Detailed script extraction is handled in _sniff_script_json if it's JSON
        # Here we just look for raw strings in scripts
        m3u8_pattern = re.compile(r'https?://[^\s"\'>]+\.m3u8[^\s"\']*', re.IGNORECASE)
        for script in soup.find_all('script'):
            if script.string:
                matches = m3u8_pattern.findall(script.string)
                for match in matches:
                    resources.append(Resource(
                        url=match,
                        resource_type=ResourceType.M3U8,
                        referer=base_url
                    ))
                    
        return self._deduplicate(resources)

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Resource]:
        """Extract image resources from HTML."""
        resources = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src:
                continue
            
            absolute_url = urljoin(base_url, src)
            
            # Skip tiny images
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
        
        return self._deduplicate(resources)
    
    def _extract_text_content(self, soup: BeautifulSoup, base_url: str) -> List[Resource]:
        """
        Extract structed text content.
        
        Strategies:
        1. Quotes (e.g., quotes.toscrape.com)
        2. Article body (<article>)
        3. Simple paragraphs if dense
        """
        resources = []
        
        # 1. Quote Extraction
        quotes = soup.find_all(class_='quote')
        for q in quotes:
            text = q.find(class_='text')
            author = q.find(class_='author')
            tags = q.find_all(class_='tag')
            
            if text:
                content = text.get_text(strip=True)
                author_name = author.get_text(strip=True) if author else "Unknown"
                tag_list = [t.get_text(strip=True) for t in tags]
                
                resources.append(Resource(
                    url=base_url, # Associated with page URL
                    resource_type=ResourceType.RICH_TEXT,
                    title=f"Quote by {author_name}",
                    content=content,
                    metadata={
                        'author': author_name,
                        'tags': tag_list,
                        'type': 'quote'
                    }
                ))
        
        if resources:
            return resources
            
        # 2. Article Extraction
        article = soup.find('article')
        if article:
            content = article.get_text(separator='\n\n', strip=True)
            if len(content) > 100:
                resources.append(Resource(
                    url=base_url,
                    resource_type=ResourceType.TEXT,
                    title=soup.title.string if soup.title else "Article Content",
                    content=content,
                    metadata={'type': 'article'}
                ))
                return resources

        # 3. Fallback: Main Content Area
        main = soup.find('main') or soup.find(id='content') or soup.find(class_='content')
        if main:
            content = main.get_text(separator='\n\n', strip=True)
            if len(content) > 200:
                 resources.append(Resource(
                    url=base_url,
                    resource_type=ResourceType.TEXT,
                    title="Page Content",
                    content=content,
                    metadata={'type': 'general_content'}
                ))
        
        return resources

    def _sniff_script_json(self, soup: BeautifulSoup) -> List[Resource]:
        """Sniff JSON data in <script> tags (e.g. __INITIAL_STATE__)."""
        resources = []
        # Pattern to find JSON objects assigned to variables
        # Look for window.X = {...} or var X = {...}
        # This is a simple heuristic
        
        scripts = soup.find_all('script')
        for script in scripts:
            if not script.string:
                continue
                
            # Example: data = {...}
            # Simple check for likely JSON content
            if 'window.__INITIAL_STATE__' in script.string or 'window.__NUXT__' in script.string:
                try:
                    # Extract the JSON part (very basic extraction)
                    match = re.search(r'=\s*({.*})', script.string)
                    if match:
                        json_str = match.group(1)
                        # Clean up trailing semicolons if caught
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        
                        data = json.loads(json_str) 
                        resources.append(Resource(
                            url='',
                            resource_type=ResourceType.JSON_DATA,
                            title="Detected Script JSON",
                            content=json.dumps(data, indent=2, ensure_ascii=False),
                            metadata={'source': 'script_sniffing'}
                        ))
                except:
                    pass
                    
        return resources

    def _deduplicate(self, resources: List[Resource]) -> List[Resource]:
        """Deduplicate resources by URL."""
        seen = set()
        unique = []
        for res in resources:
            if res.url and res.url not in seen:
                seen.add(res.url)
                unique.append(res)
            elif not res.url: # Allow content-only resources (like text)
                unique.append(res)
        return unique
