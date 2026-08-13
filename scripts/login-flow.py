#!/usr/bin/env python3
"""User-authorized browser login flow with outcome classification and optional API fetch.

Stops for CAPTCHA, MFA, password-change, account-lock, rate-limit, and automation-block
states rather than retrying them. Never put credentials in source code or shell history.
"""
import argparse
import json
import random
import sys
import time
from enum import Enum
from urllib.parse import urlparse


class LoginResult(Enum):
    SUCCESS = "SUCCESS"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    TWO_FACTOR = "TWO_FACTOR"
    RATE_LIMITED = "RATE_LIMITED"
    AUTOMATION_BLOCKED = "AUTOMATION_BLOCKED"
    CLOUDFLARE_BLOCKED = "CLOUDFLARE_BLOCKED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Ordered: explicit user-action/security states must beat generic failures.
ERROR_PATTERNS = {
    LoginResult.CAPTCHA_REQUIRED: ("captcha", "recaptcha", "hcaptcha", "turnstile", "verify you are human", "אימות אנושי"),
    LoginResult.TWO_FACTOR: ("two-factor", "2fa", "verification code", "authenticator", "otp", "קוד אימות", "אימות דו-שלבי"),
    LoginResult.CHANGE_PASSWORD: ("change your password", "password expired", "update password", "יש לשנות סיסמה", "סיסמה פגה", "הגיע הזמן לסיסמה חדשה"),
    LoginResult.ACCOUNT_BLOCKED: ("account locked", "account blocked", "account suspended", "חשבון חסום", "החשבון ננעל"),
    LoginResult.INVALID_PASSWORD: ("incorrect password", "wrong password", "invalid credentials", "שגיאה בסיסמה", "סיסמה שגויה", "פרטי ההתחברות שגויים", "authentication failed"),
    LoginResult.RATE_LIMITED: ("rate limit", "too many requests", "try again later", "slow down", "429"),
    LoginResult.AUTOMATION_BLOCKED: ("block automation", "automation detected", "bot detection", "automated access"),
    LoginResult.CLOUDFLARE_BLOCKED: ("attention required", "checking your browser", "cf-browser-verification", "cloudflare"),
}


def log(enabled, message):
    if enabled:
        print(f"[debug] {message}", file=sys.stderr)


def page_text(page):
    try:
        return page.inner_text("body").lower()
    except Exception:
        return ""


def selector_present(page, selector):
    if not selector:
        return False
    try:
        return page.query_selector(selector) is not None
    except Exception:
        return False


def frame_url_matches(page, fragments):
    wanted = [item.lower() for item in fragments or []]
    return any(any(item in frame.url.lower() for item in wanted) for frame in page.frames)


def classify_result(page, success_urls=(), success_selector=None, change_password_selectors=(), success_frame_urls=()):
    current_url = page.url.lower()
    if any(fragment.lower() in current_url for fragment in success_urls if fragment):
        return LoginResult.SUCCESS
    if selector_present(page, success_selector) or frame_url_matches(page, success_frame_urls):
        return LoginResult.SUCCESS
    if any(selector_present(page, selector) for selector in change_password_selectors):
        return LoginResult.CHANGE_PASSWORD
    body = page_text(page)
    for result, patterns in ERROR_PATTERNS.items():
        if any(pattern in body for pattern in patterns):
            return result
    return LoginResult.UNKNOWN_ERROR


def wait_for_selector_retry(page, selector, attempts=2, timeout_ms=10_000, debug=False):
    for attempt in range(attempts):
        try:
            page.wait_for_selector(selector, timeout=timeout_ms)
            return
        except Exception:
            if attempt + 1 == attempts:
                raise
            pause = 0.5 * (attempt + 1)
            log(debug, f"selector not ready; retrying in {pause:.1f}s")
            page.wait_for_timeout(int(pause * 1000))


def harvest_api(page, api_url, method="GET", headers=None):
    """Fetch a same-origin API after a successful user-authorized login."""
    page_origin = urlparse(page.url).netloc
    api_origin = urlparse(api_url).netloc
    if not api_origin or api_origin != page_origin:
        raise ValueError("--harvest must be same-origin as the authenticated page")
    cookies = page.context.cookies()
    token = next((c["value"] for c in cookies if "xsrf" in c["name"].lower() or "csrf" in c["name"].lower()), None)
    request_headers = dict(headers or {})
    if token:
        request_headers.setdefault("X-XSRF-TOKEN", token)
        request_headers.setdefault("X-CSRF-TOKEN", token)
    return page.evaluate(
        """async ({url, method, headers}) => {
          const response = await fetch(url, {method, headers, credentials: 'include'});
          const text = await response.text();
          const type = response.headers.get('content-type') || '';
          let data = text;
          if (type.includes('json')) { try { data = JSON.parse(text); } catch (_) {} }
          return {status: response.status, type: type.includes('json') ? 'json' : 'text', data};
        }""",
        {"url": api_url, "method": method, "headers": request_headers},
    )


def login(url, fields, submit_selector, success_urls=(), success_selector=None,
          change_password_selectors=(), success_frame_urls=(), humanize=False,
          wait_ms=3000, timeout_ms=30_000, retries=1, debug=False):
    from cloakbrowser import launch_context
    started = time.monotonic()
    ctx = launch_context(humanize=humanize)
    page = ctx.new_page()
    retryable = {LoginResult.UNKNOWN_ERROR, LoginResult.TIMEOUT}
    try:
        for attempt in range(retries + 1):
            try:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                for selector, value in fields:
                    wait_for_selector_retry(page, selector, debug=debug)
                    page.fill(selector, value)
                wait_for_selector_retry(page, submit_selector, attempts=2, timeout_ms=5000, debug=debug)
                page.click(submit_selector)
                page.wait_for_timeout(wait_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                result = classify_result(page, success_urls, success_selector, change_password_selectors, success_frame_urls)
                log(debug, f"attempt={attempt + 1} result={result.value} elapsed={time.monotonic()-started:.2f}s")
                if result == LoginResult.SUCCESS:
                    return result, page, ctx
                if result in retryable and attempt < retries:
                    page.wait_for_timeout(random.randint(800, 1600) * (attempt + 1))
                    continue
                ctx.close()
                return result, None, None
            except Exception as exc:
                log(debug, f"attempt={attempt + 1} exception={type(exc).__name__}: {exc}")
                if attempt >= retries:
                    ctx.close()
                    return LoginResult.TIMEOUT, None, None
                page.wait_for_timeout(random.randint(800, 1600) * (attempt + 1))
        ctx.close()
        return LoginResult.UNKNOWN_ERROR, None, None
    except Exception:
        ctx.close()
        raise


def main():
    parser = argparse.ArgumentParser(description="User-authorized CloakBrowser login flow")
    parser.add_argument("url")
    parser.add_argument("--field", action="append", required=True, help="CSS_SELECTOR=value (repeatable)")
    parser.add_argument("--submit", required=True)
    parser.add_argument("--success-url", action="append", default=[], help="success URL fragment (repeatable)")
    parser.add_argument("--success-selector")
    parser.add_argument("--success-frame-url", action="append", default=[])
    parser.add_argument("--change-password-selector", action="append", default=[])
    parser.add_argument("--harvest", help="same-origin API URL to GET after success")
    parser.add_argument("--harvest-method", default="GET")
    parser.add_argument("--humanize", action="store_true")
    parser.add_argument("--wait", type=int, default=3000)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    fields = [item.split("=", 1) for item in args.field]
    if any(len(item) != 2 or not item[0] for item in fields):
        parser.error("each --field must be CSS_SELECTOR=value")
    result, page, ctx = login(args.url, fields, args.submit, args.success_url, args.success_selector,
                              args.change_password_selector, args.success_frame_url, args.humanize,
                              args.wait, retries=args.retries, debug=args.debug)
    output = {"result": result.value, "url": args.url}
    print(f"Result: {result.value}")
    if result == LoginResult.SUCCESS and page and ctx:
        try:
            output["current_url"] = page.url
            if args.harvest:
                output["harvest"] = harvest_api(page, args.harvest, args.harvest_method)
                print(f"Harvest status: {output['harvest']['status']}")
        finally:
            ctx.close()
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(output, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
