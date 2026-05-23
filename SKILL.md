---
name: web-scraper
description: Scrape any website using the best available tool — CloakBrowser for anti-bot sites, Scrapling for fast parsing, Playwright for JS-heavy pages, or web_fetch for simple ones. Use when web_fetch fails, site is blocked by Cloudflare/anti-bot, need to extract structured data from web pages, scrape protected sites, or automate browser interactions. Triggers on "scrape", "blocked", "Cloudflare", "anti-bot", "extract data from site", "web_fetch failed", "can't access site".
---

# Web Scraper — Universal

## Decision tree (try in order)

### 1. `web_fetch` — simple pages, no JS needed
Built-in OpenClaw tool. Fast, no overhead. Fails on anti-bot or JS-rendered content.

### 2. CloakBrowser — anti-bot protected sites (yad2, Cloudflare, etc.)
Binary-level stealth Chromium. Bypasses Cloudflare, reCAPTCHA, FingerprintJS.
```python
from cloakbrowser import launch
browser = launch()
page = browser.new_page()
page.goto(url, timeout=30000)
page.wait_for_timeout(5000)  # let JS render
content = page.content()     # full HTML
text = page.inner_text("body")  # visible text
browser.close()
```
**When:** yad2, any Cloudflare site, sites that block bots, CAPTCHA pages.

### 3. Scrapling — fast HTML parsing + adaptive selectors
```python
from scrapling import Fetcher, StealthFetcher, PlayWrightFetcher

# Simple fetch + parse
page = Fetcher().get(url)
products = page.css('.product-card')
for p in products:
    print(p.css_first('.title').text, p.css_first('.price').text)

# With stealth (httpx-based, no browser)
page = StealthFetcher().get(url)

# With full browser (Playwright-backed)
page = PlayWrightFetcher().get(url)
```
**When:** Need structured data extraction, CSS selectors, fast bulk parsing.

### 4. Playwright + stealth patches — JS pages without full CloakBrowser
```python
from playwright.sync_api import sync_playwright
# See skills/playwright-stealth for stealth patches
```
**When:** JS-rendered pages, lighter than CloakBrowser, when stealth isn't critical.

### 5. SerpAPI — Google search results (Hebrew/English)
```bash
source ~/.openclaw/.env
curl "https://serpapi.com/search.json?api_key=$SERPAPI_KEY&engine=google&q=QUERY&gl=il&hl=he"
```
**When:** Need search snippets, don't need full page. 250/month limit.

## Installed tools status
| Tool | Status | Best for |
|------|--------|----------|
| web_fetch | ✅ built-in | Simple HTML pages |
| CloakBrowser | ✅ 0.3.28 | Anti-bot sites (Cloudflare, yad2) |
| Scrapling | ✅ 0.4.8 | Fast parsing, CSS selectors |
| Playwright | ✅ 1.58.2 | JS-rendered pages |
| SerpAPI | ✅ (250/mo) | Google search snippets |
| Brave Search | ✅ built-in | English web search |

## 6. Login Flow — authenticated scraping with error classification
Inspired by israeli-bank-scrapers. Handles: navigate → fill → submit → classify → optional API harvest.
```bash
# Basic login
python3 scripts/login-flow.py "https://example.com/login" \
  --field "#email=user@example.com" \
  --field "#password=secret123" \
  --submit "#login-btn" \
  --success-url "/dashboard"

# Login + harvest internal API after auth
python3 scripts/login-flow.py "https://example.com/login" \
  --field "#email=user@example.com" \
  --field "#password=secret123" \
  --submit "button[type=submit]" \
  --success-url "/dashboard" \
  --harvest "https://example.com/api/v1/data" \
  --humanize

# Save result to JSON
python3 scripts/login-flow.py "https://example.com/login" \
  --field "#user=admin" --field "#pass=1234" \
  --submit ".submit" --success-selector ".welcome" \
  --output result.json
```

### Login result classification
Returns precise enum instead of true/false:
| Result | Meaning |
|---|---|
| SUCCESS | Login successful |
| INVALID_PASSWORD | Wrong credentials |
| ACCOUNT_BLOCKED | Too many attempts / locked |
| CHANGE_PASSWORD | Password expired |
| CAPTCHA_REQUIRED | CAPTCHA/challenge detected |
| TWO_FACTOR | 2FA code required |
| RATE_LIMITED | 429 / too many requests |
| CLOUDFLARE_BLOCKED | Anti-bot challenge |
| TIMEOUT | Page didn't load |

Supports Hebrew + English error patterns automatically.

### Post-login API harvesting
After successful login, harvest data from internal APIs using the authenticated session:
- Auto-extracts XSRF/CSRF tokens from cookies
- Executes `fetch()` within page context (session cookies sent automatically)
- Returns JSON or text response
- Much more reliable than DOM scraping for structured data

### Python API (for scripting)
```python
from scripts.login_flow import login, harvest_api, LoginResult

result, page, browser = login(
    url="https://example.com/login",
    fields=[("#email", "user@test.com"), ("#pass", "secret")],
    submit_selector="button[type=submit]",
    success_url="/dashboard",
    humanize=True,
    retries=2,
)

if result == LoginResult.SUCCESS:
    data = harvest_api(page, "https://example.com/api/data")
    print(data)
    browser.close()
```

## Quick reference scripts
```bash
# Generic CloakBrowser scrape
python3 scripts/cloak-scrape.py "https://example.com"

# Extract text only
python3 scripts/cloak-scrape.py "https://example.com" --text

# Extract with CSS selector
python3 scripts/cloak-scrape.py "https://example.com" --css ".product-card"

# Login + scrape authenticated content
python3 scripts/login-flow.py "https://site.com/login" \
  --field "#user=me" --field "#pass=secret" \
  --submit "#login" --success-url "/home" \
  --harvest "https://site.com/api/data"
```

## Rules
- **Always try web_fetch first** — it's fastest and cheapest
- **If blocked** → CloakBrowser (binary stealth, most reliable)
- **If need fast parsing** → Scrapling (no browser overhead)
- **If need login** → login-flow.py with CloakBrowser stealth
- **SerpAPI is limited** — 250/month, use sparingly
- **Close browsers!** Server has 8GB RAM, don't leak browser processes
- **Never store real credentials in scripts** — use env vars or prompt
