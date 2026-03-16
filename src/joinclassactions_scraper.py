"""
JoinClassActions scraper - Scrapes class action lawsuit URLs from XML sitemap.
"""
import logging
from typing import List
from .scraper import BaseScraper


class JoinClassActionsScraper(BaseScraper):
    """Scraper for joinclassactions.com XML sitemap."""
    
    def __init__(self, logger: logging.Logger, timeout: int = 30, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize JoinClassActions scraper.
        
        Args:
            logger: Logger instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        super().__init__(logger, timeout, max_retries, retry_delay)
        self.source_name = "JoinClassActions"
        self.sitemap_url = "https://joinclassactions.com/class_actions-sitemap1.xml"
    
    def scrape(self) -> List[str]:
        """
        Scrape URLs from JoinClassActions XML sitemap.
        Only includes URLs containing 'data-breach'.
        Also applies the BaseScraper lastmod (yesterday->now UTC) filter via parse_xml_sitemap().
        """
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Scraping {self.source_name}")
        self.logger.info(f"{'='*60}")

        try:
            urls = self.parse_xml_sitemap(self.sitemap_url)

            # Filter: only keep URLs containing the keyword
            keyword = "data-breach"
            filtered = [u for u in urls if keyword in u.lower()]

            # Remove duplicates while preserving order (extra safety)
            filtered = list(dict.fromkeys(filtered))

            self.logger.info(
                f"JoinClassActions: {len(urls)} URLs after lastmod filter, "
                f"{len(filtered)} URLs after keyword filter ('{keyword}')"
            )
            return filtered

        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}", exc_info=True)
            return []
