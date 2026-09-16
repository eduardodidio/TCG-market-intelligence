"""Liga price debug tool — screenshot + HTML dump + parser output.

Usage:
    python scripts/liga_debug.py "Elspeth, Storm Slayer"
    python scripts/liga_debug.py "Elspeth, Storm Slayer" --collector-number 367
    python scripts/liga_debug.py "Elspeth, Storm Slayer" --no-headless

Produces:
    scripts/debug_output/screenshot.png   — what the browser sees
    scripts/debug_output/prices.html      — raw price-relevant HTML
    scripts/debug_output/parsed.json      — what our parser extracts
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.providers.liga.parser import parse_card_prices, parse_edition_options
from src.providers.liga.url import liga_url_for_card_name

OUTPUT_DIR = Path(__file__).parent / "debug_output"


def run_debug(card_name: str, collector_number: str | None = None, headless: bool = True):
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(exist_ok=True)

    url = liga_url_for_card_name(card_name)
    print(f"Card: {card_name}")
    print(f"URL:  {url}")
    if collector_number:
        print(f"Collector #: {collector_number}")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
        )
        page = context.new_page()

        print("Navigating to Liga Magic...")
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        print(f"HTTP status: {response.status if response else 'N/A'}")

        # Wait for price elements
        try:
            page.wait_for_selector('[class*="preco"], :text("R$")', timeout=8000)
            print("Price elements found on page")
        except Exception:
            print("WARNING: No price elements found within 8s")
            page.wait_for_timeout(2000)

        # Get full HTML before edition selection
        html_before = page.content()

        # Parse editions available
        editions = parse_edition_options(html_before)
        if editions:
            print(f"\nEdition options ({len(editions)}):")
            for val, cn in editions[:20]:
                marker = " <-- MATCH" if cn == collector_number else ""
                print(f"  value={val}  collector_number={cn}{marker}")
            if len(editions) > 20:
                print(f"  ... and {len(editions) - 20} more")

        # Select edition if requested
        edition_selected = False
        if collector_number and editions:
            matches = [(val, cn) for val, cn in editions if cn == collector_number]
            if matches:
                edition_value = matches[0][0]
                print(f"\nSelecting edition: {edition_value}")
                try:
                    page.evaluate(f"editionsCard.changeEdition('{edition_value}')")
                    page.wait_for_timeout(2000)
                    try:
                        page.wait_for_selector("div.price-mkp div.price", timeout=5000)
                    except Exception:
                        pass
                    edition_selected = True
                    print("Edition selected successfully")
                except Exception as e:
                    print(f"Edition selection FAILED: {e}")
            else:
                print(f"\nWARNING: No edition matches collector_number={collector_number}")
                print(f"Available: {[cn for _, cn in editions]}")

        # Screenshot
        screenshot_path = OUTPUT_DIR / "screenshot.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\nScreenshot saved: {screenshot_path}")

        # Also take a cropped screenshot of just the price area
        try:
            price_el = page.query_selector('[class*="price-mkp"], [class*="preco"]')
            if price_el:
                price_screenshot = OUTPUT_DIR / "screenshot_price.png"
                # Scroll to price area and capture viewport
                price_el.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                page.screenshot(path=str(price_screenshot))
                print(f"Price area screenshot: {price_screenshot}")
        except Exception:
            pass

        # Get final HTML
        html = page.content()
        final_url = page.url

        browser.close()

    print(f"Final URL: {final_url}")
    print(f"HTML length: {len(html)} chars")

    # Save price-relevant HTML sections
    price_html_path = OUTPUT_DIR / "prices.html"
    price_sections = []

    # Extract price-mkp sections
    for m in re.finditer(
        r'<div\s+class="price-mkp".*?</div>\s*</div>\s*</div>\s*</div>', html, re.DOTALL
    ):
        price_sections.append(f"<!-- price-mkp section -->\n{m.group(0)}")

    # Extract any elements with 'preco' class
    for m in re.finditer(r'<[^>]*class="[^"]*preco[^"]*"[^>]*>.*?</\w+>', html, re.DOTALL):
        price_sections.append(f"<!-- preco class -->\n{m.group(0)}")

    # Extract all R$ occurrences with context
    for m in re.finditer(r".{0,100}R\$[^<]{0,30}.{0,50}", html):
        price_sections.append(f"<!-- R$ context -->\n{m.group(0)}")

    # Extract title
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        price_sections.insert(0, f"<!-- page title -->\n{title_match.group(0)}")

    # Extract edition dropdown
    edition_match = re.search(
        r'<select[^>]*id="[^"]*edition[^"]*"[^>]*>.*?</select>', html, re.DOTALL | re.IGNORECASE
    )
    if edition_match:
        price_sections.insert(1, f"<!-- edition dropdown -->\n{edition_match.group(0)}")

    price_html = (
        "\n\n" + "=" * 80 + "\n\n".join(price_sections)
        if price_sections
        else "NO PRICE SECTIONS FOUND"
    )
    price_html_path.write_text(price_html, encoding="utf-8")
    print(f"Price HTML saved: {price_html_path}")

    # Save full HTML too (for deeper investigation)
    full_html_path = OUTPUT_DIR / "full_page.html"
    full_html_path.write_text(html, encoding="utf-8")
    print(f"Full HTML saved: {full_html_path}")

    # Run our parser
    parsed = parse_card_prices(html, card_name)
    parsed_json = {
        "card_name": parsed.get("card_name"),
        "normal": {k: str(v) if v else None for k, v in parsed.get("normal", {}).items()},
        "foil": {k: str(v) if v else None for k, v in parsed.get("foil", {}).items()},
        "edition_selected": edition_selected,
        "editions_available": len(editions),
    }

    parsed_path = OUTPUT_DIR / "parsed.json"
    parsed_path.write_text(json.dumps(parsed_json, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Parsed output saved: {parsed_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("PARSER OUTPUT:")
    n, f = parsed["normal"], parsed["foil"]
    print(f"  Normal: low={n['low']}  mid={n['mid']}  high={n['high']}")
    print(f"  Foil:   low={f['low']}  mid={f['mid']}  high={f['high']}")

    # What the sweep would store
    mid = parsed["normal"].get("mid")
    low = parsed["normal"].get("low")
    high = parsed["normal"].get("high")
    stored = mid or low or high
    print(f"\n  Sweep would store (mid preference): R$ {stored}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug Liga Magic price parsing")
    parser.add_argument("card_name", help="Card name to search")
    parser.add_argument("--collector-number", "-cn", help="Collector number for edition selection")
    parser.add_argument("--no-headless", action="store_true", help="Show the browser window")
    args = parser.parse_args()

    run_debug(args.card_name, args.collector_number, headless=not args.no_headless)
