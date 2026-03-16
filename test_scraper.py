#!/usr/bin/env python3
"""
Test script to demonstrate URL scraping without sending emails.
Useful for testing the scraping functionality before setting up email.
"""
import sys
from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import config
from src.logger import setup_logger
from src.storage import URLStorage
from src.joinclassactions_scraper import JoinClassActionsScraper
from src.rankiteo_scraper import RankiteoScraper


def main():
    """Test the scraper without email functionality."""
    print("="*70)
    print("URL SCRAPER TEST (No Email)")
    print("="*70)
    
    # Setup logger
    logger = setup_logger('url_scraper_test', config.LOGS_DIR)
    
    try:
        # Initialize components
        print("\nInitializing components...")
        
        # Separate storage for each source
        joinclassactions_storage = URLStorage(config.JOINCLASSACTIONS_URLS_FILE, logger)
        rankiteo_storage = URLStorage(config.RANKITEO_URLS_FILE, logger)
        
        # Initialize both scrapers
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
        
        # Show current stats
        joinclassactions_stats = joinclassactions_storage.get_stats()
        rankiteo_stats = rankiteo_storage.get_stats()
        
        print(f"\nCurrent storage stats:")
        print(f"  JoinClassActions URLs: {joinclassactions_stats['total_urls']}")
        print(f"  Rankiteo URLs: {rankiteo_stats['total_urls']}")
        print(f"  Total URLs tracked: {joinclassactions_stats['total_urls'] + rankiteo_stats['total_urls']}")
        
        # Scrape all sources
        print("\n" + "="*70)
        print("Starting URL scraping...")
        print("="*70)
        
        # scraped_urls = {
        #     "classactions_sitemap": joinclassactions_scraper.scrape(),
        #     "rankiteo_blog": rankiteo_scraper.scrape()
        # }
        
        try:
            scraped_urls = {
                "classactions_sitemap": joinclassactions_scraper.scrape(),
                "rankiteo_blog": rankiteo_scraper.scrape()
            }
        finally:
            joinclassactions_scraper.close()
            rankiteo_scraper.close()


        # Close scrapers
        joinclassactions_scraper.close()
        rankiteo_scraper.close()
        
        # Process results
        print("\n" + "="*70)
        print("Results:")
        print("="*70)
        
        total_scraped = 0
        total_new = 0
        
        # Process JoinClassActions URLs
        source_name = "classactions_sitemap"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)
        
        if urls:
            new_urls = joinclassactions_storage.add_urls(urls)
            total_new += len(new_urls)
            
            print(f"\n{source_name}:")
            print(f"  Scraped: {len(urls)} URLs")
            print(f"  New: {len(new_urls)} URLs")
            
            # Show first 3 new URLs as sample
            if new_urls:
                print(f"  Sample new URLs:")
                for url in new_urls[:3]:
                    print(f"    - {url}")
                if len(new_urls) > 3:
                    print(f"    ... and {len(new_urls) - 3} more")
        else:
            print(f"\n{source_name}: No URLs found")
        
        # Process Rankiteo URLs
        source_name = "rankiteo_blog"
        urls = scraped_urls[source_name]
        total_scraped += len(urls)
        
        if urls:
            new_urls = rankiteo_storage.add_urls(urls)
            total_new += len(new_urls)
            
            print(f"\n{source_name}:")
            print(f"  Scraped: {len(urls)} URLs")
            print(f"  New: {len(new_urls)} URLs")
            
            # Show first 3 new URLs as sample
            if new_urls:
                print(f"  Sample new URLs:")
                for url in new_urls[:3]:
                    print(f"    - {url}")
                if len(new_urls) > 3:
                    print(f"    ... and {len(new_urls) - 3} more")
        else:
            print(f"\n{source_name}: No URLs found")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total URLs scraped: {total_scraped}")
        print(f"New URLs found: {total_new}")
        print(f"Total JoinClassActions URLs in storage: {joinclassactions_storage.get_stats()['total_urls']}")
        print(f"Total Rankiteo URLs in storage: {rankiteo_storage.get_stats()['total_urls']}")
        print(f"Grand total URLs in storage: {joinclassactions_storage.get_stats()['total_urls'] + rankiteo_storage.get_stats()['total_urls']}")
        
        print("\n" + "="*70)
        print("Test completed successfully!")
        print("="*70)
        print("\nNote: No email was sent. To enable email, set up your .env file")
        print("and run main.py instead.")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())