# 🌐 Global Web Scraper

[![GitHub release](https://img.shields.io/github/v/release/TopSpeed0/global-web-scraper?style=flat-square)](https://github.com/TopSpeed0/global-web-scraper/releases)
[![License: MIT](https://img.shields.io/github/license/TopSpeed0/global-web-scraper?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![CloakBrowser](https://img.shields.io/badge/CloakBrowser-0.6.4-2ea44f?style=flat-square&logo=googlechrome&logoColor=white)](https://pypi.org/project/cloakbrowser/)
[![Scrapling](https://img.shields.io/badge/Scrapling-0.5-ff6600?style=flat-square)](https://github.com/D4Vinci/Scrapling)
[![Playwright](https://img.shields.io/badge/Playwright-1.64.1-6B3FA0?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-E34F26?style=flat-square)](https://openclaw.ai)

> Universal web scraper that picks the best tool for the job — from simple HTTP fetch to full stealth browser automation. Includes **login flow automation**, **API harvesting**, **error classification**, and support for **OpenClaw native providers** (Firecrawl, Tavily, Exa).

## ⚡ One-Prompt Install

```
Install the skill from https://github.com/TopSpeed0/global-web-scraper.git
```

Or manually:
```bash
git clone https://github.com/TopSpeed0/global-web-scraper.git ~/.openclaw/workspace/skills/web-scraper
cd ~/.openclaw/workspace/skills/web-scraper
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m patchright install chromium
.venv/bin/python -m cloakbrowser install  # downloads stealth Chromium (~200MB)
```

Run the helper scripts with `.venv/bin/python` (or activate it with `source .venv/bin/activate`) so project dependencies remain isolated.

## 📋 Prerequisites

| Dependency | Required? | Install |
|-----------|-----------|---------|
| **Python 3.10+** | ✅ Yes | `apt install python3` |
| **CloakBrowser** | ✅ Yes | `pip install cloakbrowser && python3 -m cloakbrowser install` |
| **Scrapling** | ✅ Yes | `pip install "scrapling[fetchers]"` |
| **Playwright** | ✅ Yes | `pip install playwright && python3 -m playwright install chromium` |
| **Patchright** | ✅ Yes | `pip install patchright` (needed by Scrapling stealth) |
| **Firecrawl API** | Optional | [firecrawl.dev](https://firecrawl.dev) — managed extraction + autonomous research |
| **Tavily API** | Optional | [tavily.com](https://tavily.com) — AI-optimized search + URL extraction |
| **Exa API** | Optional | [exa.ai](https://exa.ai) — neural search + content extraction |
| **SerpAPI** | Optional | [serpapi.com](https://serpapi.com) — Google search (250 free/month) |

## 🧠 Decision Tree

```
Need to scrape a URL?
├── Simple page, no JS? ──────────────── web_fetch (built-in)
├── web_fetch failed / JS-heavy? ──────── Firecrawl (managed, no local browser)
├── Anti-bot / Cloudflare / CAPTCHA? ──── CloakBrowser (binary stealth)
├── Need structured extraction? ────────── Scrapling (fast CSS/XPath parsing)
├── Need login + authenticated data? ──── Login Flow (CloakBrowser + auth)
├── Need search results? ─────────────── web_search / Exa / Tavily
└── Need autonomous research? ─────────── Firecrawl Agent
```

## 🚀 Usage

### CloakBrowser — Stealth scraping (bypasses Cloudflare, yad2, CAPTCHAs)

```bash
# Full HTML
python3 scripts/cloak-scrape.py "https://protected-site.com"

# Text only
python3 scripts/cloak-scrape.py "https://protected-site.com" --text

# CSS selector extraction
python3 scripts/cloak-scrape.py "https://protected-site.com" --css ".product-card"

# Hebrew site with locale + timezone
python3 scripts/cloak-scrape.py "https://yad2.co.il" --locale he-IL --timezone Asia/Jerusalem

# Human-like behavior (Bézier mouse, typing delays, scroll)
python3 scripts/cloak-scrape.py "https://protected-site.com" --humanize

# Careful mode for heavily monitored sites
python3 scripts/cloak-scrape.py "https://protected-site.com" --careful

# Persistent profile (stay logged in across runs)
python3 scripts/cloak-scrape.py "https://site.com" --profile ./my-profile

# With proxy + save output
python3 scripts/cloak-scrape.py "https://site.com" --proxy socks5://proxy:1080 -o output.txt
```

### Scrapling — Fast parsing (no browser overhead)

```bash
# Full text extraction
python3 scripts/scrapling-extract.py "https://example.com"

# CSS selector
python3 scripts/scrapling-extract.py "https://example.com" --css ".product-card"

# Stealth mode (patchright-based, no CDP signals)
python3 scripts/scrapling-extract.py "https://example.com" --stealth

# Full browser mode (Playwright-backed)
python3 scripts/scrapling-extract.py "https://example.com" --browser
```

### Login Flow — Authenticated scraping with error classification

```bash
# Login + scrape
python3 scripts/login-flow.py "https://example.com/login" \
  --field "#email=user@example.com" \
  --field "#password=secret123" \
  --submit "button[type=submit]" \
  --success-url "/dashboard"

# Login + harvest internal API
python3 scripts/login-flow.py "https://example.com/login" \
  --field "#email=user@example.com" \
  --field "#password=secret123" \
  --submit "button[type=submit]" \
  --success-url "/dashboard" \
  --harvest "https://example.com/api/v1/data" \
  --humanize
```

Login result classification: `SUCCESS`, `INVALID_PASSWORD`, `ACCOUNT_BLOCKED`, `CAPTCHA_REQUIRED`, `TWO_FACTOR`, `RATE_LIMITED`, `CLOUDFLARE_BLOCKED`, `TIMEOUT`.

### Python API

```python
# CloakBrowser — stealth scraping
from cloakbrowser import launch_context
ctx = launch_context(locale="he-IL", timezone="Asia/Jerusalem", humanize=True)
page = ctx.new_page()
page.goto("https://protected-site.com", timeout=30000)
page.wait_for_timeout(5000)
data = page.inner_text("body")
ctx.close()

# Scrapling — fast parsing
from scrapling import Fetcher, StealthyFetcher
page = Fetcher().get("https://example.com")  # simple HTTP extraction
page = StealthyFetcher.fetch("https://example.com")  # Chromium-backed stealth
items = page.css('.product-card')

# Login flow
from scripts.login_flow import login, harvest_api, LoginResult
result, page, browser = login(
    url="https://example.com/login",
    fields=[("#email", "user@test.com"), ("#pass", "secret")],
    submit_selector="button[type=submit]",
    success_url="/dashboard",
)
if result == LoginResult.SUCCESS:
    data = harvest_api(page, "https://example.com/api/data")
    browser.close()
```

## 🛡️ Anti-Bot Bypass Results

| Protection | CloakBrowser | Scrapling Stealth | Playwright |
|-----------|:------------:|:-----------------:|:----------:|
| Cloudflare Turnstile | ✅ PASS | ❌ | ❌ |
| reCAPTCHA v3 | ✅ 0.9 score | ❌ | ❌ |
| FingerprintJS | ✅ PASS | ❌ | ❌ |
| BrowserScan | ✅ NORMAL | ⚠️ partial | ❌ |
| navigator.webdriver | ✅ false | ✅ false | ⚠️ with patches |
| Headless detection | ✅ "Not headless" | ⚠️ | ❌ detected |
| JS rendering | ✅ | ✅ | ✅ |
| Speed | 🐢 | 🐇 | 🐇 |

## 🌐 OpenClaw Native Providers (Optional)

These providers integrate directly with OpenClaw — no local browser needed:

| Provider | What it does | API Key |
|----------|-------------|---------|
| **Firecrawl** | Search + scrape + autonomous research + /interact | `FIRECRAWL_API_KEY` |
| **Tavily** | AI search + JS-capable URL extraction | `TAVILY_API_KEY` |
| **Exa** | Neural search + content extraction (text/highlights/summary) | `EXA_API_KEY` |

See `SKILL.md` for full configuration and usage.

## 📁 Structure

```
web-scraper/
├── SKILL.md                      # OpenClaw skill definition (decision tree + all tools)
├── README.md                     # This file
├── LICENSE                       # MIT
├── requirements.txt              # Python dependencies
├── scripts/
│   ├── cloak-scrape.py          # CloakBrowser universal scraper
│   ├── scrapling-extract.py     # Scrapling fast extractor
│   └── login-flow.py            # Login automation + API harvesting
└── references/                   # Site-specific notes
```

## ⚠️ Important Notes

- **Close browsers!** CloakBrowser spawns real Chromium — always `ctx.close()` or you'll leak RAM
- **CloakBrowser binary** is ~200MB — one-time download
- **Headless by default** — no display needed on servers
- **SerpAPI** has a 250/month limit — use sparingly

## 📜 License

MIT

---

Made with ⚡ by [TopSpeed](https://github.com/TopSpeed0)

## 2026-10 Runtime Refresh

- **CloakBrowser 0.6.4**: latest supported release; install its managed browser runtime before use.
- **Scrapling 0.5**: requires Python 3.10+; `DynamicFetcher` was removed, so use `StealthyFetcher.fetch()` for browser-backed extraction.
- **Playwright 1.64.1 / Patchright 1.64.3**: install each managed Chromium runtime after dependency upgrades.
- **Login flow**: adds `AUTOMATION_BLOCKED`, multi-signal success/change-password detection, selector retries, redacted diagnostics, and a same-origin guard for post-login API extraction.

<!-- Updated 2026-10-27: v2.3.0 — refreshed runtime pins and migrated Scrapling browser extraction to StealthyFetcher. -->
<!-- Updated 2026-08-13: v2.2.0 -->
