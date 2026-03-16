"""
Configuration management for URL scraper project.
Loads settings from secrets.local.env by default.
Set EMAIL_CONFIG_PATH to use a config file from any local path.
"""
import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DEFAULT_EMAIL_CONFIG_FILE = BASE_DIR / "secrets.local.env"
EMAIL_CONFIG_PATH_ENV = r'/Users/sharayu/CodeLab/Local Secrets/secrets.local.env'

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Data files
JOINCLASSACTIONS_URLS_FILE = DATA_DIR / "joinclassactions_urls.json"
RANKITEO_URLS_FILE = DATA_DIR / "rankiteo_urls.json"
DEXPOSE_URLS_FILE = DATA_DIR / "dexpose_urls.json"
CYBERSECGURU_URLS_FILE = DATA_DIR / "cybersecguru_urls.json"
DATABREACH_URLS_FILE = DATA_DIR / "databreach_urls.json"

# Scraping configuration
SOURCES = {
    "classactions_sitemap": "https://joinclassactions.com/class_actions-sitemap1.xml",
    "rankiteo_blog": "https://blog.rankiteo.com",
    "dexpose": "https://www.dexpose.io",
    "cybersecguru": "https://thecybersecguru.com",
    "databreach": "https://databreach.io",
}

# Request configuration
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries


def get_email_config_file() -> Path:
    """Resolve the active email config file path.

    Priority:
      1. --email-config CLI flag  (sets EMAIL_CONFIG_PATH env var)
      2. EMAIL_CONFIG_PATH_ENV    (direct path configured above)
      3. DEFAULT_EMAIL_CONFIG_FILE (project-root fallback)
    """
    cli_override = os.getenv("EMAIL_CONFIG_PATH", "").strip()
    if cli_override:
        return Path(cli_override).expanduser().resolve()
    if EMAIL_CONFIG_PATH_ENV:
        return Path(EMAIL_CONFIG_PATH_ENV).expanduser().resolve()
    return DEFAULT_EMAIL_CONFIG_FILE


EMAIL_CONFIG_FILE = get_email_config_file()


def load_email_config() -> dict:
    """Load email configuration from a .env-style secrets file.

    Parses KEY=VALUE lines (ignoring comments, section headers, and blanks)
    and maps the following keys to the dict the rest of the codebase expects:

        SMTP_SERVER      -> smtp_server
        SMTP_PORT        -> smtp_port   (int)
        USE_SSL          -> use_ssl     (bool)
        SENDER_EMAIL     -> sender_email
        SENDER_PASSWORD  -> sender_password
        RECEIVER_EMAILS  -> receiver_emails  (list, comma-separated)
    """
    cfg_path = EMAIL_CONFIG_FILE
    if not cfg_path.exists():
        raise ValueError(
            f"Missing email config file: {cfg_path}. "
            f"Create secrets.local.env or set EMAIL_CONFIG_PATH."
        )

    # Parse all KEY=VALUE pairs from the file
    env_vars: dict = {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments, section headers, and lines without '='
            if not line or line.startswith("#") or line.startswith("[") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()

    # Map to the expected config dict
    cfg: dict = {}

    if "SMTP_SERVER" in env_vars:
        cfg["smtp_server"] = env_vars["SMTP_SERVER"]
    if "SMTP_PORT" in env_vars:
        try:
            cfg["smtp_port"] = int(env_vars["SMTP_PORT"])
        except ValueError:
            cfg["smtp_port"] = 587
    if "USE_SSL" in env_vars:
        cfg["use_ssl"] = env_vars["USE_SSL"].lower() in ("true", "1", "yes")
    if "SENDER_EMAIL" in env_vars:
        cfg["sender_email"] = env_vars["SENDER_EMAIL"]
    if "SENDER_PASSWORD" in env_vars:
        cfg["sender_password"] = env_vars["SENDER_PASSWORD"]
    if "RECEIVER_EMAILS" in env_vars:
        cfg["receiver_emails"] = [
            e.strip() for e in env_vars["RECEIVER_EMAILS"].split(",") if e.strip()
        ]

    if not cfg:
        raise ValueError(
            f"No email config keys found in {cfg_path}. "
            f"Expected SMTP_SERVER, SENDER_EMAIL, etc."
        )

    return cfg


# Email configuration (loaded once at import time)
_email_cfg = load_email_config()

SMTP_SERVER = _email_cfg.get("smtp_server", "smtp.gmail.com")
SMTP_PORT = int(_email_cfg.get("smtp_port", 587))
USE_SSL = bool(_email_cfg.get("use_ssl", False))

SMTP_USERNAME = _email_cfg.get("sender_email")
SMTP_PASSWORD = _email_cfg.get("sender_password")

EMAIL_FROM = SMTP_USERNAME
EMAIL_TO = _email_cfg.get("receiver_emails", [])


def validate_config() -> bool:
    cfg_path = str(EMAIL_CONFIG_FILE)
    errors = []

    if not SMTP_USERNAME:
        errors.append(f"sender_email is missing in {cfg_path}")
    if not SMTP_PASSWORD:
        errors.append(f"sender_password is missing in {cfg_path}")
    if not EMAIL_TO or not isinstance(EMAIL_TO, list):
        errors.append(f"receiver_emails must be a non-empty list in {cfg_path}")

    if errors:
        raise ValueError(
            "Configuration errors:\n" +
            "\n".join(f"  - {e}" for e in errors)
        )

    return True
