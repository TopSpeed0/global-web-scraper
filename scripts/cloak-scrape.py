#!/usr/bin/env python3
"""
Universal CloakBrowser scraper — works on anti-bot protected sites.
Usage:
  python3 cloak-scrape.py "https://example.com"              # full HTML
  python3 cloak-scrape.py "https://example.com" --text       # visible text only
  python3 cloak-scrape.py "https://example.com" --css ".card" # CSS selector extraction
  python3 cloak-scrape.py "https://example.com" --wait 8000  # custom wait (ms)
  python3 cloak-scrape.py "https://example.com" --humanize   # human-like behavior
  python3 cloak-scrape.py "https://example.com" --locale he-IL --timezone Asia/Jerusalem
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="CloakBrowser universal scraper")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--text", action="store_true", help="Extract visible text only")
    parser.add_argument("--css", help="CSS selector to extract")
    parser.add_argument("--wait", type=int, default=5000, help="Wait time in ms (default 5000)")
    parser.add_argument("--max", type=int, default=50, help="Max items for CSS selector")
    parser.add_argument("--chars", type=int, default=15000, help="Max chars output (default 15000)")
    parser.add_argument("--humanize", action="store_true", help="Human-like mouse/keyboard/scroll")
    parser.add_argument("--careful", action="store_true", help="Slower humanize preset (heavily monitored sites)")
    parser.add_argument("--locale", default=None, help="BCP 47 locale (e.g. en-US, he-IL)")
    parser.add_argument("--timezone", default=None, help="IANA timezone (e.g. Asia/Jerusalem)")
    parser.add_argument("--proxy", default=None, help="Proxy URL (http/socks5)")
    parser.add_argument("--profile", default=None, help="Persistent profile dir (stay logged in)")
    parser.add_argument("--output", "-o", default=None, help="Save output to file")
    args = parser.parse_args()

    human_preset = "careful" if args.careful else "default"

    if args.profile:
        from cloakbrowser import launch_persistent_context

        ctx = launch_persistent_context(
            args.profile,
            humanize=args.humanize or args.careful,
            human_preset=human_preset,
            locale=args.locale,
            timezone=args.timezone,
            proxy=args.proxy,
        )
        page = ctx.new_page()
        browser = None  # persistent context closes differently
    else:
        from cloakbrowser import launch_context

        ctx = launch_context(
            humanize=args.humanize or args.careful,
            human_preset=human_preset,
            locale=args.locale,
            timezone=args.timezone,
            proxy=args.proxy,
        )
        page = ctx.new_page()
        browser = None

    try:
        page.goto(args.url, timeout=30000)
        page.wait_for_timeout(args.wait)

        title = page.title()
        print(f"📄 {title}")
        print(f"🔗 {page.url}\n")

        output = ""

        if args.css:
            elements = page.query_selector_all(args.css)
            print(f"Found {len(elements)} elements matching '{args.css}':\n")
            lines = []
            for i, el in enumerate(elements[: args.max], 1):
                text = el.inner_text().strip()
                if text:
                    line = f"{i}. {text[:200]}"
                    lines.append(line)
                    print(line)
            output = "\n".join(lines)
        elif args.text:
            output = page.inner_text("body")[: args.chars]
            print(output)
        else:
            output = page.content()[: args.chars]
            print(output)

        if args.output and output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"\n💾 Saved to {args.output}")

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
