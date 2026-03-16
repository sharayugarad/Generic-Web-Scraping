# Generic-Web-Scraping

## Email config (keep credentials local)

By default, the app reads `config/email_config.json`.

If your real `email_config.json` is stored elsewhere, pass its path:

```bash
python main.py --email-config /absolute/path/to/email_config.json
```

Or set an environment variable:

```bash
export EMAIL_CONFIG_PATH=/absolute/path/to/email_config.json
python main.py
```
