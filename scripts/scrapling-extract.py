#!/usr/bin/env python3
"""
Fast HTML extraction using Scrapling (no browser needed for simple sites).
Usage:
  python3 scrapling-extract.py "https://example.com"
  python3 scrapling-extract.py "https://example.com" --css ".product-card"
  python3 scrapling-extract.py "https://example.com" --css "h2, .title"
  python3 scrapling-extract.py "https://example.com" --stealth
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Fast HTML extraction using Scrapling")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--css", help="CSS selector to extract elements")
    parser.add_argument("--stealth", action="store_true", help="Use StealthFetcher (httpx-based)")
    parser.add_argument("--browser", action="store_true", help="Use PlayWrightFetcher (full browser)")
    parser.add_argument("--limit", type=int, default=50, help="Max elements to show (default 50)")
    parser.add_argument("--chars", type=int, default=10000, help="Max chars for full text (default 10000)")
    args = parser.parse_args()

    if args.browser:
        from scrapling import PlayWrightFetcher
        fetcher = PlayWrightFetcher()
    elif args.stealth:
        from scrapling import StealthFetcher
        fetcher = StealthFetcher()
    else:
        from scrapling import Fetcher
        fetcher = Fetcher()

    page = fetcher.get(args.url)

    print(f"📄 Status: {page.status}")
    print(f"🔗 {args.url}\n")

    if args.css:
        elements = page.css(args.css)
        print(f"Found {len(elements)} elements matching '{args.css}':\n")
        for i, el in enumerate(elements[: args.limit], 1):
            text = el.text.strip() if el.text else ""
            if text:
                print(f"{i}. {text[:200]}")
    else:
        # Full text extraction
        body = page.css("body")
        if body:
            text = body[0].text.strip() if body[0].text else ""
            print(text[: args.chars])
        else:
            print("[No body content found]")


if __name__ == "__main__":
    main()
