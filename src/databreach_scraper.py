"""
Databreach scraper - Scrapes URLs from databreach.io post sitemap.
Only returns URLs whose lastmod is within yesterday (00:00 UTC) to now.
"""
import logging
from typing import List
from .scraper import BaseScraper


class DatabreachScraper(BaseScraper):
    """Scraper for databreach.io."""

    def __init__(
        self,
        logger: logging.Logger,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Initialize Databreach scraper.

        Args:
            logger: Logger instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        super().__init__(logger, timeout, max_retries, retry_delay)
        self.source_name = "Databreach"
        self.sitemap_url = "https://databreach.io/post-sitemap.xml"

    def scrape(self) -> List[str]:
        """
        Scrape URLs from the databreach.io post sitemap.
        Only URLs modified between yesterday (00:00 UTC) and now are returned.

        Returns:
            List of discovered URLs from yesterday to now
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Scraping {self.source_name}")
        self.logger.info(f"{'='*60}")

        try:
            urls = self.parse_xml_sitemap_filtered(self.sitemap_url)
            self.logger.info(
                f"Successfully scraped {len(urls)} URLs from {self.source_name}"
            )
            return urls

        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
            return []
