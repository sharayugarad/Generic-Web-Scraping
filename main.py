#!/usr/bin/env python3
"""
Daily URL Scraper - Main Script

This script scrapes URLs from multiple sources, tracks them in a JSON file,
and emails only new URLs that haven't been seen before.

Usage:
    python main.py
    python main.py --email-config /absolute/path/to/secrets.local.env
    python main.py --remove-date YYYY-MM-DD
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _bootstrap_email_config_path() -> None:
    """Allow passing email config path before importing config.py."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--email-config",
        dest="email_config",
        help="Path to local secrets.local.env",
    )
    args, _ = parser.parse_known_args()
    if args.email_config:
        os.environ["EMAIL_CONFIG_PATH"] = args.email_config


_bootstrap_email_config_path()

from src.logger import setup_logger
from src.storage import URLStorage


def _parse_runtime_args() -> argparse.Namespace:
    """Parse runtime arguments after config bootstrap."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--email-config",
        dest="email_config",
        help="Path to local secrets.local.env",
    )
    parser.add_argument(
        "--remove-date",
        dest="remove_date",
        help="Remove URLs first seen on YYYY-MM-DD from all storage files, then exit.",
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = _parse_runtime_args()

    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Setup logger
    logger = setup_logger('url_scraper', logs_dir)
    
    logger.info("="*70)
    logger.info("Starting Daily URL Scraper")
    logger.info("="*70)
    
    try:
        if args.remove_date:
            try:
                datetime.strptime(args.remove_date, "%Y-%m-%d")
            except ValueError:
                logger.error("Invalid --remove-date. Use format YYYY-MM-DD.")
                return 1

            logger.info("\nInitializing components...")
            data_dir = PROJECT_ROOT / "data"
            data_dir.mkdir(exist_ok=True)
            joinclassactions_storage = URLStorage(data_dir / "joinclassactions_urls.json", logger)
            rankiteo_storage = URLStorage(data_dir / "rankiteo_urls.json", logger)
            dexpose_storage = URLStorage(data_dir / "dexpose_urls.json", logger)
            cybersecguru_storage = URLStorage(data_dir / "cybersecguru_urls.json", logger)
            databreach_storage = URLStorage(data_dir / "databreach_urls.json", logger)

            logger.info("\n" + "="*70)
            logger.info(f"Removing URLs first seen on {args.remove_date}...")
            logger.info("="*70)

            removed_joinclassactions = joinclassactions_storage.remove_urls_seen_on(args.remove_date)
            removed_rankiteo = rankiteo_storage.remove_urls_seen_on(args.remove_date)
            removed_dexpose = dexpose_storage.remove_urls_seen_on(args.remove_date)
            removed_cybersecguru = cybersecguru_storage.remove_urls_seen_on(args.remove_date)
            removed_databreach = databreach_storage.remove_urls_seen_on(args.remove_date)

            total_removed = (
                len(removed_joinclassactions) +
                len(removed_rankiteo) +
                len(removed_dexpose) +
                len(removed_cybersecguru) +
                len(removed_databreach)
            )
            logger.info(f"Removed JoinClassActions URLs: {len(removed_joinclassactions)}")
            logger.info(f"Removed Rankiteo URLs: {len(removed_rankiteo)}")
            logger.info(f"Removed Dexpose URLs: {len(removed_dexpose)}")
            logger.info(f"Removed CyberSecGuru URLs: {len(removed_cybersecguru)}")
            logger.info(f"Removed Databreach URLs: {len(removed_databreach)}")
            logger.info(f"Total removed URLs: {total_removed}")
            return 0

        import config
        from src.joinclassactions_scraper import JoinClassActionsScraper
        from src.rankiteo_scraper import RankiteoScraper
        from src.dexpose_scraper import DexposeScraper
        from src.cybersecguru_scraper import CyberSecGuruScraper
        from src.databreach_scraper import DatabreachScraper
        from src.email_sender import EmailSender

        # Initialize components
        logger.info("\nInitializing components...")

        # Separate storage for each source
        joinclassactions_storage = URLStorage(config.JOINCLASSACTIONS_URLS_FILE, logger)
        rankiteo_storage = URLStorage(config.RANKITEO_URLS_FILE, logger)
        dexpose_storage = URLStorage(config.DEXPOSE_URLS_FILE, logger)
        cybersecguru_storage = URLStorage(config.CYBERSECGURU_URLS_FILE, logger)
        databreach_storage = URLStorage(config.DATABREACH_URLS_FILE, logger)

        # Validate configuration
        logger.info("Validating configuration...")
        config.validate_config()
        logger.info("Configuration validated successfully")
        
        # Initialize all scrapers
        joinclassactions_scraper = JoinClassActionsScraper(
            logger=logger,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        rankiteo_scraper = RankiteoScraper(
            logger=logger,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        dexpose_scraper = DexposeScraper(
            logger=logger,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        cybersecguru_scraper = CyberSecGuruScraper(
            logger=logger,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        databreach_scraper = DatabreachScraper(
            logger=logger,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            retry_delay=config.RETRY_DELAY
        )
        
        email_sender = EmailSender(
            smtp_server=config.SMTP_SERVER,
            smtp_port=config.SMTP_PORT,
            username=config.SMTP_USERNAME,
            password=config.SMTP_PASSWORD,
            from_email=config.EMAIL_FROM,
            logger=logger
        )
        
        # Show current stats
        joinclassactions_stats = joinclassactions_storage.get_stats()
        rankiteo_stats = rankiteo_storage.get_stats()
        dexpose_stats = dexpose_storage.get_stats()
        cybersecguru_stats = cybersecguru_storage.get_stats()
        databreach_stats = databreach_storage.get_stats()

        total_urls = (joinclassactions_stats['total_urls'] +
                     rankiteo_stats['total_urls'] +
                     dexpose_stats['total_urls'] +
                     cybersecguru_stats['total_urls'] +
                     databreach_stats['total_urls'])

        logger.info(f"\nCurrent storage stats:")
        logger.info(f"  JoinClassActions URLs: {joinclassactions_stats['total_urls']}")
        logger.info(f"  Rankiteo URLs: {rankiteo_stats['total_urls']}")
        logger.info(f"  Dexpose URLs: {dexpose_stats['total_urls']}")
        logger.info(f"  CyberSecGuru URLs: {cybersecguru_stats['total_urls']}")
        logger.info(f"  Databreach URLs: {databreach_stats['total_urls']}")
        logger.info(f"  Total URLs tracked: {total_urls}")
        
        # Scrape all sources
        logger.info("\n" + "="*70)
        logger.info("Starting URL scraping...")
        logger.info("="*70)
        
        try:
            scraped_urls = {
                "classactions_sitemap": joinclassactions_scraper.scrape(),
                "rankiteo_blog": rankiteo_scraper.scrape(),
                "dexpose": dexpose_scraper.scrape(),
                "cybersecguru": cybersecguru_scraper.scrape(),
                "databreach": databreach_scraper.scrape(),
            }
        finally:
            joinclassactions_scraper.close()
            rankiteo_scraper.close()
            dexpose_scraper.close()
            cybersecguru_scraper.close()
            databreach_scraper.close()
        
        # Process results and identify new URLs
        logger.info("\n" + "="*70)
        logger.info("Processing results...")
        logger.info("="*70)
        
        new_urls_by_source = {}
        total_scraped = 0
        total_new = 0
        
        # Process JoinClassActions URLs
        source_name = "classactions_sitemap"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)
        
        if urls:
            new_urls = joinclassactions_storage.add_urls(urls)
            new_urls_by_source[source_name] = new_urls
            total_new += len(new_urls)
            
            logger.info(f"\n{source_name}:")
            logger.info(f"  Scraped: {len(urls)} URLs")
            logger.info(f"  New: {len(new_urls)} URLs")
        else:
            logger.info(f"\n{source_name}: No URLs found")
            new_urls_by_source[source_name] = []
        
        # Process Rankiteo URLs
        source_name = "rankiteo_blog"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)
        
        if urls:
            new_urls = rankiteo_storage.add_urls(urls)
            new_urls_by_source[source_name] = new_urls
            total_new += len(new_urls)
            
            logger.info(f"\n{source_name}:")
            logger.info(f"  Scraped: {len(urls)} URLs")
            logger.info(f"  New: {len(new_urls)} URLs")
        else:
            logger.info(f"\n{source_name}: No URLs found")
            new_urls_by_source[source_name] = []
        
        # Process Dexpose URLs - NEW SECTION
        source_name = "dexpose"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)
        
        if urls:
            new_urls = dexpose_storage.add_urls(urls)
            new_urls_by_source[source_name] = new_urls
            total_new += len(new_urls)
            
            logger.info(f"\n{source_name}:")
            logger.info(f"  Scraped: {len(urls)} URLs")
            logger.info(f"  New: {len(new_urls)} URLs")
        else:
            logger.info(f"\n{source_name}: No URLs found")
            new_urls_by_source[source_name] = []
        
        # Process CyberSecGuru URLs
        source_name = "cybersecguru"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)

        if urls:
            new_urls = cybersecguru_storage.add_urls(urls)
            new_urls_by_source[source_name] = new_urls
            total_new += len(new_urls)

            logger.info(f"\n{source_name}:")
            logger.info(f"  Scraped: {len(urls)} URLs")
            logger.info(f"  New: {len(new_urls)} URLs")
        else:
            logger.info(f"\n{source_name}: No URLs found")
            new_urls_by_source[source_name] = []

        # Process Databreach URLs
        source_name = "databreach"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)

        if urls:
            new_urls = databreach_storage.add_urls(urls)
            new_urls_by_source[source_name] = new_urls
            total_new += len(new_urls)

            logger.info(f"\n{source_name}:")
            logger.info(f"  Scraped: {len(urls)} URLs")
            logger.info(f"  New: {len(new_urls)} URLs")
        else:
            logger.info(f"\n{source_name}: No URLs found")
            new_urls_by_source[source_name] = []

        # Summary
        logger.info("\n" + "="*70)
        logger.info("SUMMARY")
        logger.info("="*70)
        logger.info(f"Total URLs scraped: {total_scraped}")
        logger.info(f"New URLs found: {total_new}")
        logger.info(f"Total JoinClassActions URLs in storage: {joinclassactions_storage.get_stats()['total_urls']}")
        logger.info(f"Total Rankiteo URLs in storage: {rankiteo_storage.get_stats()['total_urls']}")
        logger.info(f"Total Dexpose URLs in storage: {dexpose_storage.get_stats()['total_urls']}")
        logger.info(f"Total CyberSecGuru URLs in storage: {cybersecguru_storage.get_stats()['total_urls']}")
        logger.info(f"Total Databreach URLs in storage: {databreach_storage.get_stats()['total_urls']}")

        grand_total = (joinclassactions_storage.get_stats()['total_urls'] +
                      rankiteo_storage.get_stats()['total_urls'] +
                      dexpose_storage.get_stats()['total_urls'] +
                      cybersecguru_storage.get_stats()['total_urls'] +
                      databreach_storage.get_stats()['total_urls'])
        logger.info(f"Grand total URLs in storage: {grand_total}")
        
        # Send email if there are new URLs (or always send daily report)
        logger.info("\n" + "="*70)
        logger.info("Sending email report...")
        logger.info("="*70)
        
        if total_new > 0:
            logger.info(f"Found {total_new} new URL(s). Sending email...")
            success = email_sender.send_report(config.EMAIL_TO, new_urls_by_source)
            
            if success:
                logger.info("Email sent successfully!")
            else:
                logger.error("Failed to send email")
                return 1
        else:
            logger.info("No new URLs found today. Sending notification email...")
            success = email_sender.send_report(config.EMAIL_TO, new_urls_by_source)
            
            if success:
                logger.info("Notification email sent successfully!")
            else:
                logger.error("Failed to send email")
                return 1
        
        logger.info("\n" + "="*70)
        logger.info("Daily URL scraper completed successfully!")
        logger.info("="*70)
        
        return 0
        
    except ValueError as e:
        logger.error(f"\nConfiguration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
