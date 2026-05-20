#!/usr/bin/env python3
"""
Universal CloakBrowser scraper — works on anti-bot protected sites.
Usage:
  python3 cloak-scrape.py "https://example.com"              # full HTML
  python3 cloak-scrape.py "https://example.com" --text       # visible text only
  python3 cloak-scrape.py "https://example.com" --css ".card" # CSS selector extraction
  python3 cloak-scrape.py "https://example.com" --wait 8000  # custom wait (ms)
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="CloakBrowser universal scraper")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--text", action="store_true", help="Extract visible text only")
    parser.add_argument("--css", help="CSS selector to extract")
    parser.add_argument("--wait", type=int, default=5000, help="Wait time in ms (default 5000)")
    parser.add_argument("--max", type=int, default=50, help="Max items for CSS selector")
    parser.add_argument("--humanize", action="store_true", help="Human-like behavior")
    args = parser.parse_args()

    from cloakbrowser import launch
    
    browser = launch(humanize=args.humanize)
    page = browser.new_page()
    
    try:
        page.goto(args.url, timeout=30000)
        page.wait_for_timeout(args.wait)
        
        title = page.title()
        print(f"📄 {title}")
        print(f"🔗 {page.url}\n")
        
        if args.css:
            elements = page.query_selector_all(args.css)
            print(f"Found {len(elements)} elements matching '{args.css}':\n")
            for i, el in enumerate(elements[:args.max], 1):
                text = el.inner_text().strip()
                if text:
                    print(f"{i}. {text[:200]}")
        elif args.text:
            text = page.inner_text("body")
            print(text[:10000])
        else:
            print(page.content()[:15000])
    
    finally:
        browser.close()

if __name__ == "__main__":
    main()
