# X399 Hunter-Seeker 🏹

A serverless GitOps scraping pipeline to hunt for X399 motherboards on Carousell (and other platforms).

## Architecture

- **Orchestrator**: GitHub Actions (Cron schedule)
- **Scrapers**: Playwright (Primary) + curl_cffi (Backup/Bypass)
- **Data Store**: Git History (JSON snapshots)
- **Alerts**: Discord Webhooks
- **Proxy**: Residential Proxy support (Authenticated)

## Setup

### 1. Secrets
You MUST configure the following secrets in your GitHub Repository settings:

- `PROXY_URL`: The full proxy connection string.
  - Format: `http://user:password@host:port`
  - **IMPORTANT**: Do not commit this string to any file!
- `DISCORD_WEBHOOK`: Your Discord Webhook URL for alerts.
- `EBAY_API_KEY`: (Optional) If you implement the eBay API scraper.

### 2. Configuration
Edit `config/targets.yaml` to change search queries and price filters.

### 3. Local Development
To run locally, you need to set the environment variables manually:

```bash
# Install
pip install -r requirements.txt
playwright install

# Run (Example)
export PROXY_URL="http://user:pass@host:port"
python scrapers/carousell.py --config config/targets.yaml --output data/test_run.json
```

## Structure
```
x399-hunter/
├── .github/workflows/   # CI/CD Pipeline
├── scrapers/           # Python scraper logic
├── data/               # Output JSONs (Git is the DB)
├── analytics/          # Z-score Analysis
└── config/             # YAML Config
```
