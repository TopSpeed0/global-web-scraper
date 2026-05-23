#!/usr/bin/env python3
"""
Login flow automation with CloakBrowser — inspired by israeli-bank-scrapers patterns.
Handles: navigate → fill fields → submit → classify result → optional API harvesting.

Usage:
  # Basic login
  python3 login-flow.py "https://example.com/login" \
    --field "#email=user@example.com" \
    --field "#password=secret123" \
    --submit "#login-btn" \
    --success-url "/dashboard"

  # Login + harvest API after auth
  python3 login-flow.py "https://example.com/login" \
    --field "#email=user@example.com" \
    --field "#password=secret123" \
    --submit "#login-btn" \
    --success-url "/dashboard" \
    --harvest "https://example.com/api/data"

  # With humanize (bypass behavioral detection)
  python3 login-flow.py "https://example.com/login" \
    --field "#email=user@example.com" \
    --field "#password=secret123" \
    --submit "button[type=submit]" \
    --success-url "/dashboard" \
    --humanize
"""

import sys
import json
import argparse
from enum import Enum


class LoginResult(Enum):
    SUCCESS = "SUCCESS"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    TWO_FACTOR = "TWO_FACTOR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    CLOUDFLARE_BLOCKED = "CLOUDFLARE_BLOCKED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Common error patterns across sites
ERROR_PATTERNS = {
    LoginResult.INVALID_PASSWORD: [
        "incorrect password", "wrong password", "invalid credentials",
        "שגיאה בסיסמה", "סיסמה שגויה", "פרטי ההתחברות שגויים",
        "login failed", "authentication failed",
    ],
    LoginResult.ACCOUNT_BLOCKED: [
        "account locked", "account blocked", "account suspended",
        "חשבון חסום", "החשבון ננעל", "too many attempts",
    ],
    LoginResult.CHANGE_PASSWORD: [
        "change your password", "password expired", "update password",
        "יש לשנות סיסמה", "סיסמה פגה",
    ],
    LoginResult.CAPTCHA_REQUIRED: [
        "captcha", "verify you are human", "אימות אנושי",
        "recaptcha", "hcaptcha", "challenge",
    ],
    LoginResult.TWO_FACTOR: [
        "two-factor", "2fa", "verification code", "authenticator",
        "קוד אימות", "אימות דו-שלבי", "sms code",
    ],
    LoginResult.RATE_LIMITED: [
        "rate limit", "too many requests", "try again later",
        "429", "slow down",
    ],
    LoginResult.CLOUDFLARE_BLOCKED: [
        "attention required", "checking your browser",
        "cf-browser-verification", "cloudflare",
    ],
}


def classify_result(page, success_url=None, success_selector=None):
    """Classify login result by checking URL, page content, and error patterns."""
    current_url = page.url.lower()
    
    # Check success conditions
    if success_url and success_url.lower() in current_url:
        return LoginResult.SUCCESS
    
    if success_selector:
        try:
            el = page.query_selector(success_selector)
            if el:
                return LoginResult.SUCCESS
        except Exception:
            pass
    
    # Check error patterns in page content
    try:
        body_text = page.inner_text("body").lower()
    except Exception:
        body_text = ""
    
    for result, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in body_text:
                return result
    
    # Check HTTP status via response
    return LoginResult.UNKNOWN_ERROR


def harvest_api(page, api_url, method="GET", headers=None):
    """After successful login, harvest data from internal API using session cookies."""
    
    # Extract cookies including XSRF/CSRF tokens
    cookies = page.context.cookies()
    xsrf_cookie = next((c for c in cookies if 'xsrf' in c['name'].lower() or 'csrf' in c['name'].lower()), None)
    
    extra_headers = {}
    if xsrf_cookie:
        extra_headers['X-XSRF-TOKEN'] = xsrf_cookie['value']
        extra_headers['X-CSRF-TOKEN'] = xsrf_cookie['value']
    
    if headers:
        extra_headers.update(headers)
    
    # Execute fetch within page context (uses session cookies automatically)
    result = page.evaluate(f"""
        async () => {{
            const headers = {json.dumps(extra_headers)};
            const resp = await fetch("{api_url}", {{
                method: "{method}",
                headers: headers,
                credentials: "include"
            }});
            const contentType = resp.headers.get("content-type") || "";
            if (contentType.includes("json")) {{
                return {{ status: resp.status, data: await resp.json(), type: "json" }};
            }}
            return {{ status: resp.status, data: await resp.text(), type: "text" }};
        }}
    """)
    
    return result


def login(url, fields, submit_selector, success_url=None, success_selector=None,
          humanize=False, wait_ms=3000, timeout_ms=30000, retries=2):
    """
    Execute login flow with retry and error classification.
    
    Args:
        url: Login page URL
        fields: List of (selector, value) tuples
        submit_selector: CSS selector for submit button
        success_url: URL fragment that indicates success
        success_selector: CSS selector that indicates success
        humanize: Use human-like typing/clicking
        wait_ms: Wait after submit (ms)
        timeout_ms: Page load timeout (ms)
        retries: Number of retry attempts
    
    Returns:
        (LoginResult, page) — page is kept open on success for API harvesting
    """
    from cloakbrowser import launch
    
    browser = launch(humanize=humanize)
    page = browser.new_page()
    
    for attempt in range(retries + 1):
        try:
            # Navigate
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            page.wait_for_timeout(1000)
            
            # Fill fields
            for selector, value in fields:
                page.wait_for_selector(selector, timeout=10000)
                if humanize:
                    page.locator(selector).fill(value)
                else:
                    page.fill(selector, value)
                page.wait_for_timeout(200)
            
            # Submit
            page.wait_for_selector(submit_selector, timeout=5000)
            page.click(submit_selector)
            
            # Wait for navigation/response
            page.wait_for_timeout(wait_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            
            # Classify
            result = classify_result(page, success_url, success_selector)
            
            if result == LoginResult.SUCCESS:
                return result, page, browser
            
            # Retryable errors
            if result in (LoginResult.TIMEOUT, LoginResult.CLOUDFLARE_BLOCKED, LoginResult.UNKNOWN_ERROR):
                if attempt < retries:
                    print(f"⚠️  Attempt {attempt + 1} failed ({result.value}), retrying...")
                    page.wait_for_timeout(2000 * (attempt + 1))
                    continue
            
            # Non-retryable errors
            print(f"❌ Login failed: {result.value}")
            browser.close()
            return result, None, None
            
        except Exception as e:
            if attempt < retries:
                print(f"⚠️  Attempt {attempt + 1} error: {e}, retrying...")
                continue
            print(f"❌ All attempts failed: {e}")
            browser.close()
            return LoginResult.TIMEOUT, None, None
    
    browser.close()
    return LoginResult.UNKNOWN_ERROR, None, None


def main():
    parser = argparse.ArgumentParser(description="CloakBrowser login flow automation")
    parser.add_argument("url", help="Login page URL")
    parser.add_argument("--field", action="append", required=True,
                        help="Field to fill: '#selector=value' (repeatable)")
    parser.add_argument("--submit", required=True, help="Submit button CSS selector")
    parser.add_argument("--success-url", help="URL fragment indicating successful login")
    parser.add_argument("--success-selector", help="CSS selector indicating successful login")
    parser.add_argument("--harvest", help="API URL to fetch after successful login")
    parser.add_argument("--harvest-method", default="GET", help="HTTP method for harvest (default GET)")
    parser.add_argument("--humanize", action="store_true", help="Human-like behavior")
    parser.add_argument("--wait", type=int, default=3000, help="Wait after submit (ms)")
    parser.add_argument("--retries", type=int, default=2, help="Retry attempts")
    parser.add_argument("--output", help="Save result to JSON file")
    args = parser.parse_args()
    
    # Parse fields
    fields = []
    for f in args.field:
        selector, value = f.split("=", 1)
        fields.append((selector, value))
    
    print(f"🔐 Logging in to {args.url}")
    print(f"   Fields: {len(fields)}, Submit: {args.submit}")
    
    result, page, browser = login(
        url=args.url,
        fields=fields,
        submit_selector=args.submit,
        success_url=args.success_url,
        success_selector=args.success_selector,
        humanize=args.humanize,
        wait_ms=args.wait,
        retries=args.retries,
    )
    
    print(f"\n{'✅' if result == LoginResult.SUCCESS else '❌'} Result: {result.value}")
    
    output = {"result": result.value, "url": args.url}
    
    if result == LoginResult.SUCCESS and page:
        print(f"📍 Current URL: {page.url}")
        
        if args.harvest:
            print(f"\n🔄 Harvesting API: {args.harvest}")
            api_data = harvest_api(page, args.harvest, method=args.harvest_method)
            print(f"   Status: {api_data.get('status')}")
            print(f"   Type: {api_data.get('type')}")
            if api_data.get('type') == 'json':
                print(json.dumps(api_data.get('data', {}), indent=2, ensure_ascii=False)[:5000])
            else:
                print(str(api_data.get('data', ''))[:5000])
            output["harvest"] = api_data
        
        browser.close()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved to {args.output}")


if __name__ == "__main__":
    main()
