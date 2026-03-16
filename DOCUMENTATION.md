# Daily URL Scraper - Technical Documentation

## 1. Project Overview

The Daily URL Scraper is an automated Python tool that monitors five cybersecurity and compliance-related websites for new content. Each day it:

1. Scrapes URLs from all five target websites
2. Compares them against previously seen URLs to identify new ones
3. Stores all URLs with timestamps in per-source JSON files
4. Sends a formatted email report (HTML + CSV attachment) to configured recipients

The tool is designed to run once daily (e.g., via cron) and ensure the team never misses new data breach notices, class action lawsuits, or security articles.

---

## 2. Monitored Sources

| Source | Website | Scraping Method | Date Filtered? |
|--------|---------|-----------------|----------------|
| **JoinClassActions** | joinclassactions.com | XML sitemap, filtered to "data-breach" URLs | No |
| **Rankiteo Blog** | blog.rankiteo.com | XML sitemap with homepage fallback | No |
| **Dexpose** | dexpose.io | XML sitemap | Yes (last 24h) |
| **CyberSecGuru** | thecybersecguru.com | XML sitemap with homepage fallback | No |
| **Databreach.io** | databreach.io | XML sitemap (`post-sitemap.xml`) | Yes (last 24h) |

**Date filtering** means only URLs modified between yesterday 00:00 UTC and now are returned from the sitemap. Sources without date filtering return all sitemap URLs, but deduplication ensures only genuinely new URLs are reported.

---

## 3. Architecture

```
main.py                  Entry point - orchestrates the full workflow
config.py                Configuration (paths, SMTP, source URLs)
src/
  scraper.py             BaseScraper - shared HTTP + XML parsing logic
  joinclassactions_scraper.py   Scraper for joinclassactions.com
  rankiteo_scraper.py           Scraper for blog.rankiteo.com
  dexpose_scraper.py            Scraper for dexpose.io
  cybersecguru_scraper.py       Scraper for thecybersecguru.com
  databreach_scraper.py         Scraper for databreach.io
  storage.py             URLStorage - persistent JSON-based URL tracking
  email_sender.py        EmailSender - SMTP email reports
  logger.py              JSON-formatted logging
config/
  email_config.json      (Placeholder - actual config uses .env file)
data/
  <source>_urls.json     One JSON file per source tracking all seen URLs
logs/
  scraper.log            JSON-formatted log output
```

---

## 4. How It Works (End-to-End Flow)

```
START
  |
  v
Parse CLI arguments (--email-config, --remove-date)
  |
  v
Load SMTP credentials from secrets.local.env
  |
  v
Initialize 5 URLStorage instances (one per source)
Initialize 5 Scraper instances (one per source)
  |
  v
Scrape all 5 websites
  |  - Each scraper fetches its target URL
  |  - Parses XML sitemaps or HTML pages
  |  - Returns a list of discovered URLs
  |
  v
For each source: compare scraped URLs against stored URLs
  |  - Add new URLs to storage with timestamp
  |  - Collect list of genuinely new URLs
  |
  v
Send email report to configured recipients
  |  - HTML body with clickable links (max 100 per source)
  |  - Plain text fallback
  |  - CSV attachment with ALL new URLs
  |
  v
Log summary and exit
```

---

## 5. Key Components

### 5.1 BaseScraper (`src/scraper.py`)

The foundation all five scrapers inherit from. Provides:

- **HTTP session** with a browser-like User-Agent header
- **Retry logic** - configurable retries (default: 3) with delay between attempts
- **XML sitemap parsing** - two variants:
  - `parse_xml_sitemap()` - returns all URLs from a sitemap
  - `parse_xml_sitemap_filtered()` - returns only URLs modified in the last 24 hours
- **Date parsing** - robust handling of multiple ISO 8601 timestamp formats

### 5.2 Individual Scrapers

Each scraper extends `BaseScraper` and implements a `scrape()` method:

- **JoinClassActionsScraper** - Parses the class actions sitemap and filters for URLs containing "data-breach"
- **RankiteoScraper** - Tries multiple sitemap paths (`/sitemap.xml`, `/sitemap_index.xml`, etc.); falls back to HTML homepage scraping if no sitemaps are found
- **DexposeScraper** - Tries multiple sitemap paths with date filtering (only last 24 hours)
- **CyberSecGuruScraper** - Same strategy as Rankiteo (sitemap with homepage fallback)
- **DatabreachScraper** - Directly parses `post-sitemap.xml` with date filtering

### 5.3 URLStorage (`src/storage.py`)

Manages persistent URL tracking in JSON files. Each source has its own file.

**Storage format:**
```json
{
  "urls": ["https://example.com/article-1", "..."],
  "url_first_seen": {
    "https://example.com/article-1": "2026-03-13T10:30:45.123456"
  },
  "metadata": {
    "created_at": "2026-03-11T14:17:23.912902",
    "last_updated": "2026-03-13T04:25:43.500137",
    "total_urls": 150
  }
}
```

**Key behaviors:**
- URLs are normalized (trailing slashes removed) before comparison
- Duplicate URLs are never stored twice
- Each URL records when it was first discovered
- `add_urls()` returns only the genuinely new URLs (not previously seen)
- `remove_urls_seen_on(date)` allows purging URLs from a specific date

### 5.4 EmailSender (`src/email_sender.py`)

Sends daily reports via SMTP (default: Gmail with TLS).

**Email contents:**
- **Subject:** "Daily General Web Scraping Links"
- **HTML body:** Styled report with per-source sections, clickable links, and a summary. Limited to 100 URLs per source in the body to keep the email readable.
- **Plain text body:** Fallback for email clients that don't render HTML.
- **CSV attachment:** Complete list of all new URLs (source + URL columns), named `all_new_urls_YYYYMMDD_HHMMSS.csv`. This ensures no data is lost even if the body is truncated.

A report is sent every run, even when zero new URLs are found (serves as a health-check).

### 5.5 Logger (`src/logger.py`)

- Logs to `logs/scraper.log` in JSON format (one JSON object per line) for machine-readable analysis
- Simultaneously prints human-readable output to the console
- Includes timestamp, log level, module, function, and line number in each log entry

---

## 6. Configuration

### 6.1 Email / SMTP Credentials

Credentials are stored in a `.env`-style file (`secrets.local.env`) **outside the repository** for security. The file is resolved in this priority order:

1. `--email-config` CLI flag
2. Hardcoded path in `config.py` (`EMAIL_CONFIG_PATH_ENV`)
3. `secrets.local.env` in the project root (fallback)

**Required keys in the secrets file:**
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
USE_SSL=false
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECEIVER_EMAILS=recipient1@example.com,recipient2@example.com
```

### 6.2 Scraping Settings (in `config.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `REQUEST_TIMEOUT` | 30 seconds | HTTP request timeout |
| `MAX_RETRIES` | 3 | Retry attempts per request |
| `RETRY_DELAY` | 2 seconds | Wait time between retries |

---

## 7. Usage

### Daily run (typical usage)
```bash
python main.py
```

### Custom email config location
```bash
python main.py --email-config /path/to/secrets.local.env
```

### Remove URLs discovered on a specific date
```bash
python main.py --remove-date 2026-03-10
```
This removes all URLs first seen on March 10, 2026, from all five storage files, then exits without scraping.

---

## 8. Adding a New Source

To monitor a new website:

1. **Create a scraper** in `src/` extending `BaseScraper` (use an existing one as a template)
2. **Add a data file path** in `config.py` (e.g., `NEWSITE_URLS_FILE = DATA_DIR / "newsite_urls.json"`)
3. **Add the source URL** to the `SOURCES` dict in `config.py`
4. **Wire it into `main.py`:**
   - Import the new scraper class
   - Create a `URLStorage` instance for it
   - Create a scraper instance
   - Add scrape/process/log blocks following the existing pattern
   - Include it in the `--remove-date` section

---

## 9. Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests to target websites |
| `beautifulsoup4` / `lxml` | HTML parsing (for homepage fallback scraping) |
| `python-dotenv` | Environment variable loading |
| `certifi` | SSL certificate verification |

Install all dependencies:
```bash
pip install -r requirements.txt
```

---

## 10. Security Considerations

- SMTP credentials are stored **outside the repository** in a local secrets file
- The `.gitignore` excludes `secrets.local.env`, `.env`, and `__pycache__/` from version control
- The scraper uses a standard browser User-Agent to avoid being blocked
- All HTTP requests use TLS (HTTPS)
- SMTP connections use STARTTLS encryption
