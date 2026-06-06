---
name: web-scraper
description: >
  Scrape any website using the best available tool — CloakBrowser for anti-bot sites,
  Scrapling for fast parsing, Playwright for JS-heavy pages, web_fetch for simple ones,
  or OpenClaw native providers (Firecrawl, Tavily, Exa) for managed extraction.
  Use when web_fetch fails, site is blocked by Cloudflare/anti-bot, need to extract
  structured data from web pages, scrape protected sites, or automate browser interactions.
  Triggers on "scrape", "blocked", "Cloudflare", "anti-bot", "extract data from site",
  "web_fetch failed", "can't access site".
version: 2.0.0
---

# Web Scraper — Universal

Pick the right tool for the job. This skill covers everything from a simple URL fetch to full stealth browser automation with login flows.

## Decision Tree (try in order)

```
Need to scrape a URL?
├── Simple page, no JS? ──────────────── 1. web_fetch
├── web_fetch failed / JS-heavy? ──────── 2. Firecrawl (managed, no local browser)
├── Anti-bot / Cloudflare / CAPTCHA? ──── 3. CloakBrowser (binary stealth)
├── Need structured extraction? ────────── 4. Scrapling (fast CSS/XPath parsing)
├── Need login + authenticated data? ──── 5. Login Flow (CloakBrowser + auth)
├── Need search results, not a URL? ───── 6. web_search / Exa / Tavily
└── Need autonomous multi-page research? ─ 7. Firecrawl Agent
```

---

## 1. `web_fetch` — Simple Pages (Built-in, No Config)

Built-in OpenClaw tool. Fast, free, no overhead. Uses Readability extraction.

```javascript
await web_fetch({ url: "https://example.com/article", extractMode: "markdown" });
```

**When:** Static pages, blogs, docs, news articles without anti-bot.
**Limits:** No JS execution, blocked by anti-bot, max 50KB output.
**Fallback:** If Firecrawl API key is configured, `web_fetch` auto-falls back to Firecrawl when Readability fails.

---

## 2. Firecrawl — Managed Extraction + Search (API, No Local Browser)

Hosted service with bot circumvention, JS rendering, and caching. No local browser needed.

### As web_fetch fallback (auto)
Configure once — `web_fetch` uses it when Readability fails:
```json5
{
  plugins: { entries: { firecrawl: { enabled: true, config: {
    webFetch: { apiKey: "fc-...", onlyMainContent: true, maxAgeMs: 172800000 }
  }}}},
}
```

### As explicit scrape tool
```javascript
// firecrawl_scrape — JS-rendered extraction with format control
await firecrawl_scrape({
  url: "https://heavy-js-site.com",
  extractMode: "markdown",  // or "json" with schema
  onlyMainContent: true,
  proxy: "auto",  // auto retries with stealth proxies if basic fails
});
```

### As search provider
```javascript
// firecrawl_search — search + optional full page content in one call
await firecrawl_search({
  query: "best CRM pricing 2026",
  count: 5,
  scrapeResults: true,  // returns full page content alongside results!
});
```

### Firecrawl Agent — Autonomous Research
Give it a goal, it plans and executes multi-step web research:
```bash
# Natural language research task
firecrawl agent "find pricing plans for top 5 CRM tools, return comparison table"
```

### /interact — Post-Scrape Actions
Stay in browser session after scraping — click, fill forms, paginate:
```bash
firecrawl browser "open https://example.com"
firecrawl browser "snapshot"
firecrawl browser "scrape"
firecrawl browser close
```

**When:** JS-heavy sites, need managed infrastructure, autonomous research, structured JSON extraction.
**Cost:** Credit-based. Free tier: 1,000 credits/month. `proxy: "auto"` uses more credits than `"basic"`.
**Not installed as Python package — OpenClaw native plugin tool.**

---

## 3. CloakBrowser — Binary Stealth (Anti-Bot Sites)

Custom Chromium with 49+ C++ patches. Binary-level stealth — not JS injection.

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

### With context (one-call setup, recommended)
```python
from cloakbrowser import launch_context

ctx = launch_context(
    locale="he-IL",
    timezone="Asia/Jerusalem",
    humanize=True,
)
page = ctx.new_page()
page.goto(url)
data = page.inner_text(".content")
ctx.close()
```

### With persistent profile (stay logged in)
```python
from cloakbrowser import launch_persistent_context
ctx = launch_persistent_context("./my-profile")
page = ctx.new_page()
page.goto("https://site.com")
ctx.close()  # cookies saved
```

**When:** yad2, Cloudflare sites, CAPTCHA pages, fingerprint detection.
**Passes:** reCAPTCHA v3 (0.9 score), Cloudflare Turnstile, FingerprintJS, BrowserScan.
**See:** `skills/cloakbrowser/SKILL.md` for full API reference.

---

## 4. Scrapling — Fast HTML Parsing

Fast structured extraction with CSS/XPath selectors. No browser overhead.

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

---

## 5. Login Flow — Authenticated Scraping

CloakBrowser-based login with error classification and API harvesting.

```bash
# Login + harvest internal API after auth
python3 scripts/login-flow.py "https://example.com/login" \
  --field "#email=user@example.com" \
  --field "#password=secret123" \
  --submit "button[type=submit]" \
  --success-url "/dashboard" \
  --harvest "https://example.com/api/v1/data" \
  --humanize
```

### Login result classification
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

### Python API
```python
from scripts.login_flow import login, harvest_api, LoginResult

result, page, browser = login(
    url="https://example.com/login",
    fields=[("#email", "user@test.com"), ("#pass", "secret")],
    submit_selector="button[type=submit]",
    success_url="/dashboard",
    humanize=True,
)
if result == LoginResult.SUCCESS:
    data = harvest_api(page, "https://example.com/api/data")
    browser.close()
```

**When:** Need authenticated content, post-login API data, session cookies.
**Features:** Auto-extracts XSRF/CSRF tokens, Hebrew + English error patterns, retries.

---

## 6. Search Providers — When You Need Results, Not a Specific Page

### web_search (Brave — our default)
```javascript
await web_search({ query: "OpenClaw plugins", count: 5 });
```
Structured snippets, independent index, privacy-first. Supports `freshness`, `date_after`/`date_before`, `country`, `language`.

### Exa — Neural/Semantic Search + Content Extraction
```javascript
await web_search({
  query: "transformer architecture explained",
  type: "neural",  // or "fast", "deep", "deep-reasoning", "instant"
  contents: {
    text: true,           // full page text
    highlights: { numSentences: 3 },  // key sentences
    summary: true,        // AI summary
  },
});
```
**Killer feature:** Returns actual page content alongside search results — no separate fetch needed.
**Requires:** `EXA_API_KEY`

### Tavily — AI-Optimized Search + URL Extraction
```javascript
// Search with AI-generated answer
await tavily_search({
  query: "best CRM tools 2026",
  search_depth: "advanced",
  topic: "general",  // or "news", "finance"
  include_answer: true,
  time_range: "month",
});

// Extract content from URLs (handles JS!)
await tavily_extract({
  urls: ["https://site1.com", "https://site2.com"],
  query: "pricing plans",  // reranks chunks by relevance
  extract_depth: "advanced",  // for JS/SPAs
  chunks_per_source: 3,
});
```
**Killer feature:** `tavily_extract` handles JS-rendered pages and query-focused chunking.
**Requires:** `TAVILY_API_KEY`. Free tier: 1,000 searches/month.

### SerpAPI (Google) — Hebrew/Israeli queries
```bash
source ~/.openclaw/.env
curl "https://serpapi.com/search.json?api_key=$SERPAPI_KEY&engine=google&q=QUERY&gl=il&hl=he"
```
**When:** Need Google results specifically, Hebrew queries. 250/month free.

---

## 7. Playwright + Stealth Patches — Lighter Alternative

When CloakBrowser is overkill but you need JS execution:
```python
from playwright.sync_api import sync_playwright
# See skills/playwright-stealth for stealth patches
```
**When:** JS-rendered pages, stealth not critical.

---

## Installed Tools Status

| Tool | Version | Best For |
|------|---------|----------|
| web_fetch | ✅ built-in | Simple HTML pages |
| CloakBrowser | ✅ 0.3.31 | Anti-bot (Cloudflare, yad2, CAPTCHAs) |
| Scrapling | ✅ 0.4.8 | Fast CSS/XPath parsing |
| Playwright | ✅ 1.60.0 | JS-rendered pages |
| Brave Search | ✅ built-in | English web search (default provider) |
| SerpAPI | ✅ (250/mo) | Hebrew/Google search snippets |
| Firecrawl | ⚙️ needs API key | Managed extraction, autonomous research |
| Tavily | ⚙️ needs API key | AI search + URL extraction |
| Exa | ⚙️ needs API key | Neural search + content extraction |

## Quick Reference Scripts

```bash
# Generic CloakBrowser scrape
python3 scripts/cloak-scrape.py "https://example.com"

# Extract text only
python3 scripts/cloak-scrape.py "https://example.com" --text

# Extract with CSS selector
python3 scripts/cloak-scrape.py "https://example.com" --css ".product-card"

# CloakBrowser with locale/timezone/humanize
python3 scripts/cloak-scrape.py "https://example.com" --locale he-IL --timezone Asia/Jerusalem --humanize

# CloakBrowser with persistent profile (stay logged in)
python3 scripts/cloak-scrape.py "https://example.com" --profile ./my-profile --text

# CloakBrowser with proxy + save output
python3 scripts/cloak-scrape.py "https://example.com" --proxy socks5://proxy:1080 -o output.txt

# Scrapling structured extraction
python3 scripts/scrapling-extract.py "https://example.com" --css ".items"

# Scrapling with stealth (httpx) or full browser
python3 scripts/scrapling-extract.py "https://example.com" --stealth
python3 scripts/scrapling-extract.py "https://example.com" --browser

# Login + harvest API
python3 scripts/login-flow.py "https://site.com/login" \
  --field "#user=me" --field "#pass=secret" \
  --submit "#login" --success-url "/home" \
  --harvest "https://site.com/api/data"
```

## Rules

1. **Always try `web_fetch` first** — fastest and free
2. **If blocked / JS-heavy** → Firecrawl (if API key available) or CloakBrowser
3. **If need structured data** → Scrapling for fast parsing
4. **If need login** → `login-flow.py` with CloakBrowser stealth
5. **If need search results** → `web_search` (Brave), or Exa/Tavily for richer extraction
6. **If need autonomous research** → Firecrawl Agent
7. **Close browsers!** Server has 8GB RAM — don't leak browser processes
8. **Never store credentials in scripts** — use env vars or prompt
9. **SerpAPI is limited** — 250/month, use sparingly

<!-- Updated 2026-06-06: v2.0.0 — Added OpenClaw native providers (Firecrawl search/scrape/agent/interact, Tavily search/extract, Exa neural search), restructured decision tree, updated tool versions (CloakBrowser 0.3.31, Playwright 1.59.0), added Firecrawl as web_fetch fallback config, added Browser Sandbox docs -->
