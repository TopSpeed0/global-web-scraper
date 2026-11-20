#!/usr/bin/env python3
"""
Universal CloakBrowser scraper — works on anti-bot protected sites.
Usage:
  python3 cloak-scrape.py "https://example.com"                      # full HTML
  python3 cloak-scrape.py "https://example.com" --text               # visible text only
  python3 cloak-scrape.py "https://example.com" --css ".card"        # CSS selector extraction
  python3 cloak-scrape.py "https://example.com" --css ".card" --wait-for ".card"
  python3 cloak-scrape.py "https://example.com" --wait-for-response "/api/"
  python3 cloak-scrape.py "https://example.com" --json               # result envelope
  python3 cloak-scrape.py "https://example.com" --humanize           # human-like behavior
  python3 cloak-scrape.py "https://example.com" --locale he-IL --timezone Asia/Jerusalem
Exit code 0 on success; see README "Exit codes" for failures.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scrape_core as core  # noqa: E402

LEGACY_WAIT_MS = 5000
CHALLENGE_WAIT_MS = 20000


def parse_args():
    parser = argparse.ArgumentParser(description="CloakBrowser universal scraper")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--text", action="store_true", help="Extract visible text only")
    parser.add_argument("--css", help="CSS selector to extract")
    parser.add_argument("--wait-for", help="Wait until this CSS selector is in the DOM")
    parser.add_argument("--wait-for-url", help="Wait until the page URL matches this regex")
    parser.add_argument("--wait-for-response", help="Wait until a response whose URL matches this regex arrives")
    parser.add_argument("--wait", type=int, default=None,
                        help=f"Extra fixed wait in ms (default {LEGACY_WAIT_MS} without --wait-for*, else 0)")
    parser.add_argument("--timeout", type=int, default=30000, help="Navigation and wait timeout in ms (default 30000)")
    parser.add_argument("--retries", type=int, default=1, help="Retries on HTTP 429/5xx (default 1)")
    parser.add_argument("--max", type=int, default=50, help="Max items for CSS selector")
    parser.add_argument("--chars", type=int, default=15000, help="Max chars output (default 15000)")
    parser.add_argument("--humanize", action="store_true", help="Human-like mouse/keyboard/scroll")
    parser.add_argument("--careful", action="store_true", help="Slower humanize preset (heavily monitored sites)")
    parser.add_argument("--locale", default=None, help="BCP 47 locale (e.g. en-US, he-IL)")
    parser.add_argument("--timezone", default=None, help="IANA timezone (e.g. Asia/Jerusalem)")
    parser.add_argument("--proxy", default=None, help="Proxy URL (http/socks5)")
    parser.add_argument("--profile", default=None, help="Persistent profile dir (stay logged in)")
    parser.add_argument("--output", "-o", default=None, help="Save extracted output to file (UTF-8)")
    parser.add_argument("--json", action="store_true", help="Print the result envelope as JSON")
    args = parser.parse_args()
    if args.wait is None:
        waits_given = args.wait_for or args.wait_for_url or args.wait_for_response
        args.wait = 0 if waits_given else LEGACY_WAIT_MS
    return args


def launch(args):
    options = dict(
        humanize=args.humanize or args.careful,
        human_preset="careful" if args.careful else "default",
        locale=args.locale,
        timezone=args.timezone,
        proxy=args.proxy,
    )
    if args.profile:
        from cloakbrowser import launch_persistent_context
        return launch_persistent_context(args.profile, **options)
    from cloakbrowser import launch_context
    return launch_context(**options)


def extract(page, args, result):
    if args.css:
        elements = page.query_selector_all(args.css)
        items = [text for text in (el.inner_text().strip() for el in elements[: args.max]) if text]
        result.data = {"selector": args.css, "count": len(elements), "items": [item[:200] for item in items]}
        if not elements:
            result.fail(core.EMPTY_RESULT, f"selector '{args.css}' matched 0 elements")
        return "\n".join(f"{i}. {item[:200]}" for i, item in enumerate(items, 1))
    if args.text:
        text = page.inner_text("body")
        result.data = {"text": text[: args.chars], "truncated": len(text) > args.chars}
        if not text.strip():
            result.fail(core.EMPTY_RESULT, "page body has no visible text")
        return text[: args.chars]
    html = page.content()
    result.data = {"html": html[: args.chars], "truncated": len(html) > args.chars}
    return html[: args.chars]


def print_human(result):
    print(f"📄 {result.title or ''}")
    print(f"🔗 {result.final_url or result.url}\n")
    data = result.data or {}
    if "items" in data:
        print(f"Found {data['count']} elements matching '{data['selector']}':\n")
        for i, item in enumerate(data["items"], 1):
            print(f"{i}. {item}")
    else:
        print(data.get("text") or data.get("html") or "")


def main():
    core.configure_stdout()
    args = parse_args()
    result = core.Result(tool="cloak-scrape", url=args.url)
    output = ""
    ctx = None
    try:
        ctx = launch(args)
        page = ctx.new_page()
        navigations = []
        page.on("response", lambda r: navigations.append(r)
                if r.request.is_navigation_request() and r.frame == page.main_frame else None)
        response = core.goto_checked(page, args.url, timeout_ms=args.timeout, retries=args.retries,
                                     wait_for_response=args.wait_for_response)
        cleared = core.wait_challenge_clear(page, timeout_ms=min(args.timeout, CHALLENGE_WAIT_MS))
        last = navigations[-1] if navigations else response
        if cleared and core.classify_page(last.status if last else None) is None:
            core.wait_ready(page, selector=args.wait_for, url_regex=args.wait_for_url,
                            timeout_ms=args.timeout, fixed_ms=args.wait)
            last = navigations[-1] if navigations else response
        if last is not None:
            result.status = last.status
            result.retry_after = core.parse_retry_after(core.header(last.headers, "retry-after"))
        error = core.classify_page(result.status, page.title(), page.content())
        on_error_page = page.url.startswith("chrome-error://")
        result.final_url = (last.url if last is not None else args.url) if on_error_page else page.url
        result.title = None if on_error_page else page.title()
        if error:
            result.fail(error, f"{error} at {result.final_url}")
        else:
            output = extract(page, args, result)
    except Exception as exc:
        result.fail(core.classify_exception(exc), core.first_line(exc))
    finally:
        if ctx is not None:
            try:
                ctx.close()
            except Exception:
                pass

    if args.output and output and result.ok:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
        if not args.json:
            print(f"💾 Saved to {args.output}", file=sys.stderr)

    sys.exit(result.emit(args.json, print_human))


if __name__ == "__main__":
    main()
