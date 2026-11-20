#!/usr/bin/env python3
"""
Fast HTML extraction using Scrapling (no browser needed for simple sites).
Usage:
  python3 scrapling-extract.py "https://example.com"
  python3 scrapling-extract.py "https://example.com" --css ".product-card"
  python3 scrapling-extract.py "https://example.com" --css "h2, .title"
  python3 scrapling-extract.py "https://example.com" --stealth --wait-for ".product-card"
  python3 scrapling-extract.py "https://example.com" --json
Exit code 0 on success; see README "Exit codes" for failures.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scrape_core as core  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Fast HTML extraction using Scrapling")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--css", help="CSS selector to extract elements")
    parser.add_argument("--stealth", action="store_true", help="Use Scrapling's stealth Chromium fetcher")
    parser.add_argument("--browser", action="store_true", help="Alias for --stealth (Scrapling 0.5 removed DynamicFetcher)")
    parser.add_argument("--wait-for", help="With --stealth: wait until this CSS selector is in the DOM")
    parser.add_argument("--timeout", type=int, default=30000, help="Request/page timeout in ms (default 30000)")
    parser.add_argument("--retries", type=int, default=1, help="Retries on HTTP 429/5xx (default 1)")
    parser.add_argument("--limit", type=int, default=50, help="Max elements to show (default 50)")
    parser.add_argument("--chars", type=int, default=10000, help="Max chars for full text (default 10000)")
    parser.add_argument("--json", action="store_true", help="Print the result envelope as JSON")
    args = parser.parse_args()
    args.stealth = args.stealth or args.browser
    if args.wait_for and not args.stealth:
        parser.error("--wait-for needs --stealth (the plain HTTP fetcher does not run JavaScript)")
    return args


def fetch(args):
    if args.stealth:
        from scrapling import StealthyFetcher
        options = {"timeout": args.timeout}
        if args.wait_for:
            options["wait_selector"] = args.wait_for
        return StealthyFetcher.fetch(args.url, **options)
    from scrapling import Fetcher
    return Fetcher.get(args.url, timeout=args.timeout / 1000)


def fetch_with_retries(args):
    page = None
    for attempt in range(args.retries + 1):
        page = fetch(args)
        if attempt < args.retries and core.should_retry_status(page.status):
            title = page.css("title::text").get() or ""
            if core.is_challenge(title, page.html_content):
                return page
            retry_after = core.parse_retry_after(core.header(page.headers, "retry-after"))
            time.sleep(core.backoff_seconds(attempt, retry_after))
            continue
        return page
    return page


def element_text(el):
    return el.get_all_text(separator=" ", strip=True)


def extract(page, args, result):
    if args.css:
        elements = page.css(args.css)
        items = [text for text in (element_text(el) for el in elements[: args.limit]) if text]
        result.data = {"selector": args.css, "count": len(elements), "items": [item[:200] for item in items]}
        if not elements:
            result.fail(core.EMPTY_RESULT, f"selector '{args.css}' matched 0 elements")
        return
    body = page.css("body")
    text = body[0].get_all_text(separator="\n", strip=True) if body else ""
    result.data = {"text": text[: args.chars], "truncated": len(text) > args.chars}
    if not text:
        result.fail(core.EMPTY_RESULT, "page body has no text")


def print_human(result):
    print(f"📄 Status: {result.status}")
    print(f"🔗 {result.final_url or result.url}\n")
    data = result.data or {}
    if "items" in data:
        print(f"Found {data['count']} elements matching '{data['selector']}':\n")
        for i, item in enumerate(data["items"], 1):
            print(f"{i}. {item}")
    else:
        print(data.get("text", ""))


def main():
    core.configure_stdout()
    args = parse_args()
    result = core.Result(tool="scrapling-extract", url=args.url)
    try:
        page = fetch_with_retries(args)
        result.status = page.status
        result.final_url = str(page.url) if page.url else args.url
        result.title = page.css("title::text").get()
        result.retry_after = core.parse_retry_after(core.header(page.headers, "retry-after"))
        error = core.classify_page(page.status, result.title, page.html_content)
        if error:
            result.fail(error, f"{error} at {result.final_url}")
        else:
            extract(page, args, result)
    except Exception as exc:
        result.fail(core.classify_exception(exc), core.first_line(exc))
    sys.exit(result.emit(args.json, print_human))


if __name__ == "__main__":
    main()
