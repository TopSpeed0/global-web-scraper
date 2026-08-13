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
