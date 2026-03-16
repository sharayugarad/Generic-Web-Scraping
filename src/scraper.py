"""
Base URL scraper with common functionality for all scrapers.
"""
import time
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from xml.etree import ElementTree as ET

import requests


class BaseScraper:
    """Base scraper class with common functionality."""

    def __init__(
        self,
        logger: logging.Logger,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Initialize base scraper.

        Args:
            logger: Logger instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.logger = logger
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _is_within_yesterday_to_now(self, lastmod_text: str) -> bool:
        """
        Returns True if lastmod is between yesterday (00:00 UTC) and now (UTC).

        Robust against formats like:
          - 2026-01-15T16:01:00+00:00
          - 2026-01-15 16:01 +00:00
          - 2026-01-15 16:01+00:00
          - 2026-01-15
          - ...Z
        """
        try:
            txt = lastmod_text.strip().replace("Z", "+00:00")

            # Remove whitespace before timezone offset: "16:01 +00:00" -> "16:01+00:00"
            txt = re.sub(r"\s+([+-]\d{2}:\d{2})$", r"\1", txt)

            # Date-only (YYYY-MM-DD) -> midnight UTC
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt):
                lastmod = datetime.fromisoformat(txt).replace(tzinfo=timezone.utc)
            else:
                # If time has only HH:MM (no seconds), add :00 before timezone offset
                # e.g. "2026-01-15 16:01+00:00" or "2026-01-15T16:01+00:00"
                # The lookbehind (?<!:) prevents matching MM:SS in HH:MM:SS
                txt = re.sub(r"(?<!:)(\d{2}:\d{2})([+-]\d{2}:\d{2})$", r"\1:00\2", txt)

                lastmod = datetime.fromisoformat(txt)

                # If tzinfo missing, assume UTC
                if lastmod.tzinfo is None:
                    lastmod = lastmod.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            yesterday = (now - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            return yesterday <= lastmod <= now

        except Exception:
            return False

    def _fetch_with_retry(self, url: str) -> requests.Response:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch

        Returns:
            Response object

        Raises:
            requests.RequestException: If all retries fail
        """
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.debug(f"Fetching {url} (attempt {attempt}/{self.max_retries})")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt} failed for {url}: {e}")

                if attempt < self.max_retries:
                    self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

        self.logger.error(f"All {self.max_retries} attempts failed for {url}")
        raise last_exception

    def parse_xml_sitemap(self, sitemap_url: str) -> List[str]:
        """
        Parse URLs from an XML sitemap (no lastmod filtering).
        Returns all discovered URLs.
        """
        urls: List[str] = []

        try:
            self.logger.info(f"Parsing XML sitemap: {sitemap_url}")
            response = self._fetch_with_retry(sitemap_url)
            root = ET.fromstring(response.content)

            namespaces = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Extract all <loc> elements (works for both urlset + sitemapindex)
            loc_nodes = root.findall(".//ns:loc", namespaces)
            if not loc_nodes:
                loc_nodes = root.findall(".//loc")  # no-namespace fallback

            for loc in loc_nodes:
                if loc.text:
                    urls.append(loc.text.strip())

            # Remove duplicates while preserving order
            urls = list(dict.fromkeys(urls))

            self.logger.info(f"Found {len(urls)} URLs in sitemap")

        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML sitemap: {e}")
        except requests.RequestException as e:
            self.logger.error(f"Error fetching sitemap: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing sitemap: {e}", exc_info=True)

        return urls

    def parse_xml_sitemap_filtered(self, sitemap_url: str) -> List[str]:
        """
        Parse URLs from an XML sitemap, keeping only entries whose <lastmod>
        falls between yesterday (00:00 UTC) and now (UTC).

        Entries without a <lastmod> tag are skipped.

        Args:
            sitemap_url: URL of the XML sitemap

        Returns:
            List of discovered URLs from yesterday to now
        """
        urls: List[str] = []
        sample_count = 0

        try:
            self.logger.info(f"Parsing XML sitemap (date-filtered): {sitemap_url}")
            response = self._fetch_with_retry(sitemap_url)
            root = ET.fromstring(response.content)

            namespaces = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Prefer <url> nodes (urlset) to access <loc> + <lastmod> together
            url_nodes = root.findall(".//ns:url", namespaces)
            if not url_nodes:
                url_nodes = root.findall(".//url")  # no-namespace fallback

            for url_node in url_nodes:
                # NOTE: Do NOT use `or` to chain Element lookups — an Element
                # with text but no children evaluates to False in bool context,
                # causing `elem_a or elem_b` to skip a perfectly valid elem_a.
                loc = url_node.find("ns:loc", namespaces)
                if loc is None:
                    loc = url_node.find("loc")
                lastmod = url_node.find("ns:lastmod", namespaces)
                if lastmod is None:
                    lastmod = url_node.find("lastmod")

                if loc is None or not loc.text:
                    continue

                # Strict mode: require lastmod
                if lastmod is None or not lastmod.text:
                    continue

                if sample_count < 3:
                    self.logger.info(f"Sample lastmod raw: {lastmod.text.strip()}")
                    sample_count += 1

                if not self._is_within_yesterday_to_now(lastmod.text):
                    continue

                urls.append(loc.text.strip())

            self.logger.info(f"Found {len(urls)} URLs in sitemap (after date filter)")

        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML sitemap: {e}")
        except requests.RequestException as e:
            self.logger.error(f"Error fetching sitemap: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing sitemap: {e}", exc_info=True)

        return urls

    def close(self):
        """Close the requests session."""
        self.session.close()
