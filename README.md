# 🌐 Global Web Scraper

[![GitHub release](https://img.shields.io/github/v/release/TopSpeed0/global-web-scraper?style=flat-square)](https://github.com/TopSpeed0/global-web-scraper/releases)
[![License: MIT](https://img.shields.io/github/license/TopSpeed0/global-web-scraper?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![CloakBrowser](https://img.shields.io/badge/CloakBrowser-Stealth-2ea44f?style=flat-square&logo=googlechrome&logoColor=white)](https://github.com/nichochar/cloakbrowser)
[![Scrapling](https://img.shields.io/badge/Scrapling-0.4.8-ff6600?style=flat-square)](https://github.com/D4Vinci/Scrapling)
[![Playwright](https://img.shields.io/badge/Playwright-1.58-6B3FA0?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-E34F26?style=flat-square)](https://openclaw.ai)
[![Requirements](https://img.shields.io/badge/requirements-txt-brightgreen?style=flat-square)](requirements.txt)

> Universal web scraper that automatically picks the best tool for the job — from simple HTTP fetch to full stealth browser automation. Now with **login flow automation**, **API harvesting**, and **error classification** inspired by israeli-bank-scrapers.

## ⚡ One-Prompt Install

```
Install the skill from https://github.com/TopSpeed0/global-web-scraper.git
```

Or manually:
```bash
git clone git@github.com:TopSpeed0/global-web-scraper.git ~/.openclaw/workspace/skills/web-scraper
pip install -r requirements.txt
python3 -m cloakbrowser install  # downloads stealth Chromium (~200MB)
npx playwright install chromium
```

## 📋 Prerequisites

| Dependency | Required? | Install |
|-----------|-----------|---------|
| **Python 3.10+** | ✅ Yes | `apt install python3` |
| **CloakBrowser** | ✅ Yes | `pip install cloakbrowser && python3 -m cloakbrowser install` |
| **Scrapling** | ✅ Yes | `pip install scrapling` |
| **Playwright** | Optional | `pip install playwright && npx playwright install chromium` |
| **SerpAPI key** | Optional | [serpapi.com](https://serpapi.com) (250 free/month) |

## 🧠 How It Works

The skill uses a smart decision tree to pick the right tool:

```
web_fetch (simple pages)
    ↓ blocked?
CloakBrowser (anti-bot bypass — Cloudflare, CAPTCHA, fingerprint)
    ↓ need fast parsing?
Scrapling (CSS selectors, adaptive scraping)
    ↓ need JS rendering?
Playwright (headless browser)
    ↓ need search results?
SerpAPI (Google search snippets)
```

## 🚀 Usage

### CloakBrowser — Stealth scraping (bypasses Cloudflare, yad2, etc.)

```bash
# Full HTML
python3 scripts/cloak-scrape.py "https://protected-site.com"

# Text only
python3 scripts/cloak-scrape.py "https://protected-site.com" --text

# CSS selector extraction
python3 scripts/cloak-scrape.py "https://protected-site.com" --css ".product-card"

# Custom wait time (ms) for slow-loading pages
python3 scripts/cloak-scrape.py "https://protected-site.com" --wait 8000

# Human-like behavior (mouse movements, typing delays)
python3 scripts/cloak-scrape.py "https://protected-site.com" --humanize
```

### Scrapling — Fast parsing (no browser overhead)

```bash
# Full text extraction
python3 scripts/scrapling-extract.py "https://example.com"

# CSS selector
python3 scripts/scrapling-extract.py "https://example.com" ".product-card"
```

### Python API

```python
# CloakBrowser
from cloakbrowser import launch
browser = launch()
page = browser.new_page()
page.goto("https://protected-site.com", timeout=30000)
page.wait_for_timeout(5000)
data = page.inner_text("body")
browser.close()

# Scrapling
from scrapling import Fetcher, StealthFetcher
page = Fetcher().get("https://example.com")
items = page.css('.product-card')
for item in items:
    print(item.css_first('.title').text)
```

## 🛡️ Anti-Bot Bypass Capabilities

| Protection | CloakBrowser | Scrapling | Playwright |
|-----------|:------------:|:---------:|:----------:|
| Cloudflare | ✅ | ❌ | ❌ |
| reCAPTCHA v3 | ✅ (0.9 score) | ❌ | ❌ |
| FingerprintJS | ✅ | ❌ | ❌ |
| Cloudflare Turnstile | ✅ | ❌ | ❌ |
| navigator.webdriver | ✅ hidden | ❌ | ⚠️ with patches |
| JS rendering | ✅ | ⚠️ limited | ✅ |
| Speed | 🐢 slow | 🚀 fast | 🐇 medium |

## 📁 Structure

```
web-scraper/
├── SKILL.md                      # OpenClaw skill definition
├── README.md                     # This file
├── LICENSE                       # MIT License
├── requirements.txt              # Python dependencies
├── scripts/
│   ├── cloak-scrape.py          # Universal CloakBrowser scraper
│   └── scrapling-extract.py     # Fast Scrapling extractor
└── references/
    └── (empty — add site-specific notes here)
```

## ⚠️ Important Notes

- **Close browsers!** CloakBrowser spawns real Chromium — always `browser.close()` or you'll leak RAM
- **SerpAPI** has a 250/month free limit — use sparingly
- **CloakBrowser binary** is ~200MB — one-time download
- **Headless by default** — no display needed on servers

## 📜 License

MIT — do whatever you want with it.

---

Made with ⚡ by [TopSpeed](https://github.com/TopSpeed0)
