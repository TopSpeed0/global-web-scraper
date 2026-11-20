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

Same routing as `SKILL.md`: choose the lightest tool that works, escalate on evidence.

```
Need information from the web?
├── Need discovery / candidate URLs? ───── web_search
├── Have a simple public URL? ──────────── web_fetch
├── Need JS, pagination or UI actions? ─── OpenClaw Browser
├── Need structured CSS/XPath data? ────── Scrapling   (scripts/scrapling-extract.py)
├── Blocked by anti-bot / Cloudflare? ──── CloakBrowser (scripts/cloak-scrape.py)
└── Need a logged-in session? ──────────── Browser profile + explicit user authorization
                                           (scripts/login-flow.py)
```

Escalate when a script reports `EMPTY_RESULT` (page needs JavaScript) or `BLOCKED` / `HTTP_ERROR` 403 (anti-bot). See [Results and exit codes](#-results-and-exit-codes). Optional managed providers (Firecrawl, Tavily, Exa) are listed below.

## 🚀 Usage

### CloakBrowser — Stealth scraping (bypasses Cloudflare, yad2, CAPTCHAs)

```bash
# Full HTML
python3 scripts/cloak-scrape.py "https://protected-site.com"

# Text only
python3 scripts/cloak-scrape.py "https://protected-site.com" --text

# CSS selector extraction
python3 scripts/cloak-scrape.py "https://protected-site.com" --css ".product-card"

# Wait for the content instead of a fixed 5 s pause
python3 scripts/cloak-scrape.py "https://site.com/search" --css ".result" --wait-for ".result"

# Wait for the SPA's data request, or for a redirect to finish
python3 scripts/cloak-scrape.py "https://site.com/app" --text --wait-for-response "/api/"
python3 scripts/cloak-scrape.py "https://site.com/go" --text --wait-for-url "/landing"

# Machine-readable result envelope (see "Results and exit codes")
python3 scripts/cloak-scrape.py "https://site.com" --text --json

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

Readiness flags: `--wait-for SELECTOR`, `--wait-for-url REGEX`, `--wait-for-response REGEX`, all bounded by `--timeout MS` (default 30000). Without any of them the old fixed `--wait 5000` still applies; with one, `--wait` defaults to 0. Navigation retries on HTTP 429/5xx (`--retries`, default 1, honouring `Retry-After` up to 30 s) but never reloads an anti-bot challenge page; a challenge gets up to 20 s to clear by itself before the run reports `BLOCKED`.

### Scrapling — Fast parsing (no browser overhead)

```bash
# Full text extraction
python3 scripts/scrapling-extract.py "https://example.com"

# CSS selector
python3 scripts/scrapling-extract.py "https://example.com" --css ".product-card"

# Stealth mode (patchright-based, no CDP signals)
python3 scripts/scrapling-extract.py "https://example.com" --stealth

# Full browser mode (alias of --stealth since Scrapling 0.5)
python3 scripts/scrapling-extract.py "https://example.com" --browser

# Browser mode, wait for content
python3 scripts/scrapling-extract.py "https://example.com" --stealth --wait-for ".product-card"

# Result envelope
python3 scripts/scrapling-extract.py "https://example.com" --css ".product-card" --json
```

`--retries N` retries HTTP 429/5xx (default 1). `--timeout MS` bounds the request.

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

Login result classification: `SUCCESS`, `INVALID_PASSWORD`, `ACCOUNT_BLOCKED`, `CHANGE_PASSWORD`, `CAPTCHA_REQUIRED`, `TWO_FACTOR`, `RATE_LIMITED`, `AUTOMATION_BLOCKED`, `CLOUDFLARE_BLOCKED`, `TIMEOUT`, `UNKNOWN_ERROR`. With `--json` the result becomes the envelope's `error_type`; field values are never printed.

> The examples above show literal values for brevity. Never put a real password on the command line: it lands in shell history and the process list.

## 📦 Results and exit codes

Every script accepts `--json` and then prints one envelope:

```json
{
  "ok": false,
  "error_type": "RATE_LIMITED",
  "retryable": true,
  "message": "RATE_LIMITED at https://site.com/search",
  "hint": "Wait for retry_after seconds (or a few minutes) before retrying. Slow down.",
  "url": "https://site.com/search",
  "final_url": "https://site.com/search",
  "status": 429,
  "title": "Too Many Requests",
  "retry_after": 30.0,
  "elapsed_ms": 812,
  "tool": "scrapling-extract",
  "data": null
}
```

`data` holds `{"text", "truncated"}`, `{"html", "truncated"}` or `{"selector", "count", "items"}`. Without `--json` the scripts print as before, and failures go to stderr as `ERROR <type>: <message>` plus a hint. The exit code is set either way:

| Exit | `error_type` | Meaning | Retryable |
|---|---|---|---|
| 0 | — | Success | — |
| 1 | `UNKNOWN_ERROR` | Unclassified failure | no |
| 2 | `INVALID_ARGUMENT` | Bad arguments (also argparse usage errors) | no |
| 3 | `EMPTY_RESULT` | Selector matched nothing / no text. The page may need JavaScript. | no |
| 4 | `NOT_FOUND` | HTTP 404/410 | no |
| 5 | `HTTP_ERROR` | Other HTTP ≥ 400 | 5xx only |
| 6 | `RATE_LIMITED` | HTTP 429 (`retry_after` filled when sent) | yes |
| 7 | `BLOCKED`, `CLOUDFLARE_BLOCKED`, `AUTOMATION_BLOCKED` | Anti-bot challenge page | no |
| 8 | `TIMEOUT` | Page or awaited element too slow | yes |
| 9 | `NAVIGATION_ERROR` | DNS / connection failure | yes |
| 11 | `INVALID_PASSWORD`, `ACCOUNT_BLOCKED`, `CHANGE_PASSWORD`, `CAPTCHA_REQUIRED`, `TWO_FACTOR` | Login needs the user | no |

`login-flow.py` marks every failure as not retryable: re-running it re-submits credentials.

Challenge pages are detected from the page title and structural markers (for example `cf-browser-verification`), never from prose, so a "Performance & security by Cloudflare" footer is not a block.

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

# Login flow (run from the repository root)
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
├── requirements-dev.txt          # + pytest
├── scripts/
│   ├── cloak-scrape.py          # CloakBrowser universal scraper
│   ├── scrapling-extract.py     # Scrapling fast extractor
│   ├── login-flow.py            # CLI entry point for login_flow.py
│   ├── login_flow.py            # Login automation + API harvesting (importable)
│   └── scrape_core.py           # Checked navigation, readiness waits, result envelope
└── tests/                        # Offline tests against a local fixture server
```

## 🧪 Tests

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests                       # offline: core + Scrapling CLI
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest tests   # also CloakBrowser CLI tests
```

All tests run against `127.0.0.1` fixtures; no internet and no credentials needed.

## ⚠️ Important Notes

- **Close browsers!** CloakBrowser spawns real Chromium — always `ctx.close()` or you'll leak RAM
- **CloakBrowser binary** is ~200MB — one-time download
- **Headless by default** — no display needed on servers
- **SerpAPI** has a 250/month limit — use sparingly

## 📜 License

MIT

---

Made with ⚡ by [TopSpeed](https://github.com/TopSpeed0)

## 2026-11 Reliability Update (v2.4.0)

- **Fixed:** `scrapling-extract.py` full-text mode printed nothing (it read only the body's direct text); emoji output crashed non-UTF-8 consoles; `cloak-scrape.py -o` wrote with the system encoding; the documented Python import of the login flow failed.
- **Readiness waits:** `--wait-for`, `--wait-for-url`, `--wait-for-response` replace the fixed 5 s pause when given; navigation retries 429/5xx and honours `Retry-After`.
- **Result envelope:** `--json` on every script, a shared error taxonomy, and distinct exit codes. HTTP errors no longer exit 0.
- Patterns adapted from [eshaham/israeli-bank-scrapers](https://github.com/eshaham/israeli-bank-scrapers) (MIT): status-checked navigation with retries, readiness helpers, and results returned instead of thrown.

## 2026-10 Runtime Refresh

- **CloakBrowser 0.6.4**: latest supported release; install its managed browser runtime before use.
- **Scrapling 0.5**: requires Python 3.10+; `DynamicFetcher` was removed, so use `StealthyFetcher.fetch()` for browser-backed extraction.
- **Playwright 1.64.1 / Patchright 1.64.3**: install each managed Chromium runtime after dependency upgrades.
- **Login flow**: adds `AUTOMATION_BLOCKED`, multi-signal success/change-password detection, selector retries, redacted diagnostics, and a same-origin guard for post-login API extraction.

<!-- Updated 2026-11-20: v2.4.0 — scrapling full-text fix, readiness waits, status retries, --json result envelope and exit codes, offline tests. -->
<!-- Updated 2026-10-27: v2.3.0 — refreshed runtime pins and migrated Scrapling browser extraction to StealthyFetcher. -->
<!-- Updated 2026-08-13: v2.2.0 -->
