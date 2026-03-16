"""
CyberSecGuru scraper - Scrapes URLs from thecybersecguru.com.
"""
import logging
from typing import List
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
from .scraper import BaseScraper


class CyberSecGuruScraper(BaseScraper):
    """Scraper for thecybersecguru.com."""
    
    def __init__(self, logger: logging.Logger, timeout: int = 30, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize CyberSecGuru scraper.
        
        Args:
            logger: Logger instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        super().__init__(logger, timeout, max_retries, retry_delay)
        self.source_name = "CyberSecGuru"
        self.site_url = "https://thecybersecguru.com"
    
    def _try_sitemaps(self) -> List[str]:
        """
        Try to find and scrape sitemaps.
        
        Returns:
            List of discovered URLs
        """
        urls = []
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/post-sitemap.xml',
            '/page-sitemap.xml'
        ]
        
        for path in sitemap_paths:
            sitemap_url = self.site_url.rstrip('/') + path
            
            try:
                self.logger.info(f"Trying sitemap: {sitemap_url}")
                response = self.session.get(sitemap_url, timeout=self.timeout)
                
                if response.status_code == 200:
                    self.logger.info(f"Found sitemap at {sitemap_url}")
                    
                    # Parse XML
                    root = ET.fromstring(response.content)
                    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    
                    # Check if it's a sitemap index
                    sitemaps = root.findall('.//ns:sitemap/ns:loc', namespaces)
                    if sitemaps:
                        self.logger.info("Found sitemap index, fetching sub-sitemaps")
                        for sitemap_loc in sitemaps:
                            sub_urls = self.parse_xml_sitemap(sitemap_loc.text)
                            urls.extend(sub_urls)
                    else:
                        # Regular sitemap
                        for loc in root.findall('.//ns:loc', namespaces):
                            if loc.text:
                                urls.append(loc.text.strip())
                    
                    if urls:
                        self.logger.info(f"Found {len(urls)} URLs in sitemap")
                        return urls
                        
            except Exception as e:
                self.logger.debug(f"Sitemap not found at {sitemap_url}: {e}")
                continue
        
        self.logger.info("No sitemaps found")
        return urls
    
    def _scrape_homepage(self) -> List[str]:
        """
        Scrape URLs from the homepage.
        
        Returns:
            List of discovered URLs
        """
        urls = []
        
        try:
            self.logger.info(f"Scraping homepage: {self.site_url}")
            response = self._fetch_with_retry(self.site_url)
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = self.site_url.rstrip('/') + href
                elif not href.startswith('http'):
                    continue
                
                # Only include URLs from the same domain
                if href.startswith(self.site_url):
                    urls.append(href)
            
            # Remove duplicates while preserving order
            urls = list(dict.fromkeys(urls))
            
            self.logger.info(f"Found {len(urls)} URLs on homepage")
            
        except Exception as e:
            self.logger.error(f"Error scraping homepage: {e}")
        
        return urls
    
    def scrape(self) -> List[str]:
        """
        Scrape URLs from CyberSecGuru.
        Tries sitemaps first, then falls back to homepage scraping.
        
        Returns:
            List of discovered URLs
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Scraping {self.source_name}")
        self.logger.info(f"{'='*60}")
        
        try:
            # Try sitemaps first
            urls = self._try_sitemaps()
            
            # Fall back to homepage if no sitemap found
            if not urls:
                self.logger.info("Falling back to homepage scraping")
                urls = self._scrape_homepage()
            
            self.logger.info(f"Successfully scraped {len(urls)} URLs from {self.source_name}")
            return urls
            
        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
            return []