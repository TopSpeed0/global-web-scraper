#!/usr/bin/env python3
"""
Fast HTML extraction using Scrapling (no browser needed for simple sites).
Usage:
  python3 scrapling-extract.py "https://example.com" ".product-card"
  python3 scrapling-extract.py "https://example.com" "h2, .title"
  python3 scrapling-extract.py "https://example.com"  # full text
"""

import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: scrapling-extract.py URL [css-selector]")
        sys.exit(1)
    
    url = sys.argv[1]
    selector = sys.argv[2] if len(sys.argv) > 2 else None
    
    from scrapling import Fetcher
    
    fetcher = Fetcher()
    page = fetcher.get(url)
    
    print(f"📄 Status: {page.status}")
    print(f"🔗 {url}\n")
    
    if selector:
        elements = page.css(selector)
        print(f"Found {len(elements)} elements matching '{selector}':\n")
        for i, el in enumerate(elements[:50], 1):
            text = el.text.strip() if el.text else ""
            if text:
                print(f"{i}. {text[:200]}")
    else:
        print(page.text()[:10000] if hasattr(page, 'text') else str(page)[:10000])

if __name__ == "__main__":
    main()
