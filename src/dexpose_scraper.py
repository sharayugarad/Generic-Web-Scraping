"""
Dexpose scraper - Scrapes URLs from dexpose.io.
Only returns URLs whose lastmod is within yesterday (00:00 UTC) to now.
"""
import logging
from typing import List
from xml.etree import ElementTree as ET
from .scraper import BaseScraper


class DexposeScraper(BaseScraper):
    """Scraper for dexpose.io."""

    def __init__(
        self,
        logger: logging.Logger,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Initialize Dexpose scraper.

        Args:
            logger: Logger instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        super().__init__(logger, timeout, max_retries, retry_delay)
        self.source_name = "Dexpose"
        self.site_url = "https://www.dexpose.io"

    def _try_sitemaps(self) -> List[str]:
        """
        Try to find and scrape sitemaps, filtering by yesterday's date.

        Returns:
            List of discovered URLs from yesterday to now
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

                    # Parse XML to check if it's a sitemap index
                    root = ET.fromstring(response.content)
                    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                    # Check if it's a sitemap index
                    sitemaps = root.findall('.//ns:sitemap/ns:loc', namespaces)
                    if sitemaps:
                        self.logger.info("Found sitemap index, fetching sub-sitemaps")
                        for sitemap_loc in sitemaps:
                            sub_urls = self.parse_xml_sitemap_filtered(sitemap_loc.text)
                            urls.extend(sub_urls)
                    else:
                        # Regular sitemap — use date-filtered parsing
                        sub_urls = self.parse_xml_sitemap_filtered(sitemap_url)
                        urls.extend(sub_urls)

                    if urls:
                        self.logger.info(f"Found {len(urls)} URLs in sitemap (after date filter)")
                        return urls

            except Exception as e:
                self.logger.debug(f"Sitemap not found at {sitemap_url}: {e}")
                continue

        self.logger.info("No sitemaps found or no URLs from yesterday")
        return urls

    def scrape(self) -> List[str]:
        """
        Scrape URLs from Dexpose sitemaps.
        Only URLs modified between yesterday (00:00 UTC) and now are returned.

        Returns:
            List of discovered URLs from yesterday to now
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Scraping {self.source_name}")
        self.logger.info(f"{'='*60}")

        try:
            urls = self._try_sitemaps()
            self.logger.info(
                f"Successfully scraped {len(urls)} URLs from {self.source_name}"
            )
            return urls

        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
            return []
