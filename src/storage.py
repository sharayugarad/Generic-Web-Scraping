"""
Storage module for persisting discovered URLs in JSON format.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


class URLStorage:
    """Manages persistent storage of discovered URLs."""

    def __init__(self, storage_file: Path, logger: logging.Logger):
        """
        Initialize URL storage.

        Args:
            storage_file: Path to JSON file for storing URLs
            logger: Logger instance
        """
        self.storage_file = storage_file
        self.logger = logger
        self.data = self._load()

    def _empty_storage(self) -> dict:
        """Return default storage schema."""
        now = datetime.now().isoformat()
        return {
            "urls": [],
            "url_first_seen": {},
            "metadata": {
                "created_at": now,
                "last_updated": now,
                "total_urls": 0,
            },
        }

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent dedupe checks."""
        if not url:
            return ""
        normalized = url.strip()
        if normalized.endswith("/"):
            normalized = normalized[:-1]
        return normalized

    def _normalize_storage_data(self, data: dict) -> dict:
        """
        Upgrade legacy files to the current schema and normalize values.
        """
        if not isinstance(data, dict):
            return self._empty_storage()

        raw_urls = data.get("urls", [])
        if not isinstance(raw_urls, list):
            raw_urls = []

        normalized_urls = []
        seen = set()
        for url in raw_urls:
            if not isinstance(url, str):
                continue
            cleaned = self._normalize_url(url)
            if cleaned and cleaned not in seen:
                normalized_urls.append(cleaned)
                seen.add(cleaned)

        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        created_at = metadata.get("created_at") or datetime.now().isoformat()
        metadata["created_at"] = created_at
        metadata["last_updated"] = metadata.get("last_updated") or datetime.now().isoformat()
        metadata["total_urls"] = len(normalized_urls)

        first_seen = data.get("url_first_seen", {})
        if not isinstance(first_seen, dict):
            first_seen = {}

        normalized_first_seen: Dict[str, str] = {}
        for url in normalized_urls:
            raw_ts = first_seen.get(url)
            if isinstance(raw_ts, str) and raw_ts.strip():
                normalized_first_seen[url] = raw_ts
            else:
                normalized_first_seen[url] = created_at

        return {
            "urls": normalized_urls,
            "url_first_seen": normalized_first_seen,
            "metadata": metadata,
        }

    def _load(self) -> dict:
        """Load existing URLs from JSON file."""
        if not self.storage_file.exists():
            self.logger.info(f"Storage file not found. Creating new: {self.storage_file}")
            return self._empty_storage()

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = self._normalize_storage_data(json.load(f))
                self.logger.info(f"Loaded {len(data.get('urls', []))} existing URLs from storage")
                return data
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON file: {e}. Creating new storage.")
            return self._empty_storage()
        except Exception as e:
            self.logger.error(f"Error loading storage file: {e}")
            raise

    def _save(self) -> None:
        """Save URLs to JSON file."""
        try:
            self.data = self._normalize_storage_data(self.data)
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()
            self.data["metadata"]["total_urls"] = len(self.data["urls"])

            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            self.logger.info(f"Saved {len(self.data['urls'])} URLs to storage")
        except Exception as e:
            self.logger.error(f"Error saving storage file: {e}")
            raise

    def get_seen_urls(self) -> Set[str]:
        """
        Get set of all previously seen URLs.

        Returns:
            Set of URL strings
        """
        return set(self.data.get("urls", []))

    def add_urls(self, new_urls: List[str]) -> List[str]:
        """
        Add new URLs to storage and return only the newly added ones.

        Args:
            new_urls: List of URLs to add

        Returns:
            List of URLs that were actually new (not duplicates)
        """
        cleaned = []
        for url in new_urls:
            cleaned_url = self._normalize_url(url)
            if cleaned_url:
                cleaned.append(cleaned_url)

        seen = self.get_seen_urls()
        truly_new = [url for url in cleaned if url not in seen]

        if truly_new:
            self.data["urls"].extend(truly_new)
            first_seen_map = self.data.setdefault("url_first_seen", {})
            now = datetime.now().isoformat()
            for url in truly_new:
                first_seen_map[url] = now
            self._save()
            self.logger.info(f"Added {len(truly_new)} new URLs to storage")
        else:
            self.logger.info("No new URLs to add")

        return truly_new

    def remove_urls_seen_on(self, target_date: str) -> List[str]:
        """
        Remove URLs first seen on a specific date.

        Args:
            target_date: Date in YYYY-MM-DD format

        Returns:
            List of removed URLs
        """
        first_seen_map = self.data.setdefault("url_first_seen", {})
        urls = self.data.get("urls", [])
        kept_urls = []
        removed_urls = []

        for url in urls:
            first_seen = str(first_seen_map.get(url, ""))
            first_seen_date = first_seen.split("T")[0] if first_seen else ""
            if first_seen_date == target_date:
                removed_urls.append(url)
            else:
                kept_urls.append(url)

        if removed_urls:
            self.data["urls"] = kept_urls
            for url in removed_urls:
                first_seen_map.pop(url, None)
            self._save()
            self.logger.info(f"Removed {len(removed_urls)} URL(s) first seen on {target_date}")
        else:
            self.logger.info(f"No URLs found for date {target_date}")

        return removed_urls

    def get_stats(self) -> dict:
        """
        Get statistics about stored URLs.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_urls": len(self.data.get("urls", [])),
            "created_at": self.data.get("metadata", {}).get("created_at"),
            "last_updated": self.data.get("metadata", {}).get("last_updated"),
        }
