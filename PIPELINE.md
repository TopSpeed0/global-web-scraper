# Pipeline

## Change workflow
1. Read this file and inspect repository state.
2. Create a baseline commit before modifications.
3. Update code, documentation, and dependency constraints together.
4. Run syntax checks and focused smoke tests; record the result in the commit message or PR notes.
5. Commit and push via the SSH `origin` remote.

## Current work
- 2026-08-13: Updated Python runtime to CloakBrowser 0.5.7, Scrapling 0.4.14, Playwright 1.62.0, and Patchright 1.61.2; installed matching Playwright and Patchright Chromium builds.
- 2026-08-13: Refreshed routing/docs to v2.2.0; hardened `login-flow.py` with `AUTOMATION_BLOCKED`, selector retries, layered success/password-change detection, redacted timing diagnostics, safe resource cleanup, and same-origin post-login API harvesting.
- Verification: all three public-page extractors succeeded against `https://example.com`; login classifier and syntax smoke tests succeeded. `pip check` still reports the pre-existing unrelated OS package issue `pygobject -> pycairo`.
- 2026-11-20: v2.4.0 (improvement-plan items 0, 2, 3). Fixed `scrapling-extract.py` full-text mode (`get_all_text`), UTF-8 stdout and `-o` output, and the login-flow Python import (`login_flow.py` + `login-flow.py` CLI shim). Added `scripts/scrape_core.py`: status-checked navigation with 429/5xx retries and `Retry-After`, capture of empty-body error responses (`ERR_HTTP_RESPONSE_CODE_FAILURE`), challenge detection by title/markers with a 20 s self-clear window, `--wait-for` / `--wait-for-url` / `--wait-for-response`, and a `--json` result envelope with error taxonomy and exit codes on all scripts. README routing aligned with SKILL.md.
- Verification: `pytest tests` 55 passed with `RUN_BROWSER_TESTS=1` (local fixture server, no network). Live: books.toscrape full text 1,810 chars; quotes.toscrape `/scroll` 10 quotes in 2.3 s via `--wait-for-response` (fixed wait: 9.1 s); `/js-delayed` 0 quotes with the fixed wait vs 10 with `--wait-for`; httpbin 404/429/503 → NOT_FOUND/RATE_LIMITED/HTTP_ERROR with exit 4/6/5 in both scripts; `delay/10` with 4 s timeout → TIMEOUT; unresolvable host → NAVIGATION_ERROR. On Git Bash for Windows, set `MSYS_NO_PATHCONV=1` or arguments starting with `/` are rewritten to paths.
- 2026-10-27: Refreshed isolated runtime to CloakBrowser 0.6.4, Scrapling 0.5, Playwright 1.64.1, and Patchright 1.64.3. Migrated the CLI's obsolete `DynamicFetcher` browser path to `StealthyFetcher`; `--browser` remains a compatibility alias. Validation includes syntax/import checks, managed browser installs, public extraction, and a product-search fallback flow.
