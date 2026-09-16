"""Liga price debug tool — screenshot + HTML dump + parser output.

Usage (single card):
    python scripts/liga_debug.py "Elspeth, Storm Slayer"
    python scripts/liga_debug.py "Elspeth, Storm Slayer" --collector-number 367
    python scripts/liga_debug.py "Elspeth, Storm Slayer" -cn 367 --set-code cmm
    python scripts/liga_debug.py "Elspeth, Storm Slayer" --no-headless

Usage (batch mode):
    python scripts/liga_debug.py --batch mismatches.csv
    python scripts/liga_debug.py --batch mismatches.csv --limit 10
    python scripts/liga_debug.py --batch mismatches.csv --limit 5 --no-headless

Produces (single card):
    scripts/debug_output/screenshot.png   — what the browser sees
    scripts/debug_output/prices.html      — raw price-relevant HTML
    scripts/debug_output/parsed.json      — what our parser extracts

Produces (batch mode):
    scripts/debug_output/batch_debug.csv  — summary CSV with results
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.providers.liga.parser import parse_card_prices, parse_edition_options
from src.providers.liga.url import liga_url_for_card_name

OUTPUT_DIR = Path(__file__).parent / "debug_output"

# Delay between cards in batch mode (seconds)
BATCH_DELAY_SECONDS = 5


def format_edition_line(
    val: str,
    cn: str,
    sigla: str,
    collector_number: str | None = None,
    set_code: str | None = None,
) -> str:
    """Format a single edition line for display output."""
    marker = ""
    if collector_number and cn == collector_number:
        if set_code and sigla == set_code.lower():
            marker = " <-- MATCH (cn+sigla)"
        else:
            marker = " <-- MATCH (cn)"
    return f"  value={val}  collector_number={cn}  sigla={sigla}{marker}"


def select_edition_from_matches(
    editions: list[tuple[str, str, str]],
    collector_number: str,
    set_code: str | None = None,
) -> tuple[str | None, bool]:
    """Find the best edition match using collector_number and optional set_code.

    Uses the same disambiguation logic as provider._select_edition:
    1. Filter editions by collector_number.
    2. If set_code provided and multiple CN matches, prefer sigla match.

    Returns (edition_value, matched) or (None, False) if no match.
    """
    matches = [(val, cn, sigla) for val, cn, sigla in editions if cn == collector_number]
    if not matches:
        return None, False

    # Disambiguate by sigla when multiple editions share the same collector_number
    if set_code and len(matches) > 1:
        sc = set_code.lower()
        sigla_matches = [m for m in matches if m[2] == sc]
        if sigla_matches:
            matches = sigla_matches

    return matches[0][0], True


def run_debug(
    card_name: str,
    collector_number: str | None = None,
    set_code: str | None = None,
    headless: bool = True,
) -> dict:
    """Run debug for a single card. Returns parsed result dict."""
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(exist_ok=True)

    url = liga_url_for_card_name(card_name)
    print(f"Card: {card_name}")
    print(f"URL:  {url}")
    if collector_number:
        print(f"Collector #: {collector_number}")
    if set_code:
        print(f"Set code: {set_code}")
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
            for val, cn, sigla in editions[:20]:
                line = format_edition_line(val, cn, sigla, collector_number, set_code)
                print(line)
            if len(editions) > 20:
                print(f"  ... and {len(editions) - 20} more")

        # Select edition if requested
        edition_selected = False
        if collector_number and editions:
            edition_value, matched = select_edition_from_matches(
                editions, collector_number, set_code
            )
            if matched and edition_value:
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
                if set_code:
                    print(f"  (set_code={set_code} was also used for filtering)")
                print(f"Available: {[(cn, sigla) for _, cn, sigla in editions]}")

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

    return {
        "card_name": card_name,
        "collector_number": collector_number or "",
        "set_code": set_code or "",
        "edition_matched": edition_selected,
        "liga_mid": parsed["normal"].get("mid"),
        "liga_low": parsed["normal"].get("low"),
        "liga_high": parsed["normal"].get("high"),
        "parsed": parsed,
    }


def run_batch(
    csv_path: str,
    limit: int | None = None,
    headless: bool = True,
) -> None:
    """Run debug in batch mode — process multiple cards from a CSV file."""
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(exist_ok=True)

    input_path = Path(csv_path)
    if not input_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    # Read input CSV
    rows = _read_batch_csv(input_path)
    if not rows:
        print("ERROR: No valid rows found in CSV (need name_en column)")
        sys.exit(1)

    total = len(rows)
    if limit and limit > 0:
        rows = rows[:limit]
    print(f"Batch mode: {len(rows)} cards to process (of {total} in CSV)")
    print()

    results: list[dict] = []

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

        for idx, row in enumerate(rows, 1):
            card_name = row["name_en"]
            collector_number = row.get("collector_number", "").strip() or None
            set_code = row.get("set_code", "").strip() or None
            card_id = row.get("card_id", "").strip() or None
            our_mid = row.get("our_mid", "").strip() or None

            print(f"\n{'=' * 60}")
            print(f"[{idx}/{len(rows)}] {card_name}")
            if collector_number:
                print(f"  Collector #: {collector_number}")
            if set_code:
                print(f"  Set code: {set_code}")
            if card_id:
                print(f"  Card ID: {card_id}")

            result = _process_single_card_in_batch(
                page, card_name, collector_number, set_code, our_mid
            )
            result["card_id"] = card_id or ""
            results.append(result)

            # Rate limit between cards
            if idx < len(rows):
                print(f"  Waiting {BATCH_DELAY_SECONDS}s before next card...")
                time.sleep(BATCH_DELAY_SECONDS)

        browser.close()

    # Write output CSV
    output_path = OUTPUT_DIR / "batch_debug.csv"
    _write_batch_csv(output_path, results)
    print(f"\nBatch results saved: {output_path}")

    # Print summary
    _print_batch_summary(results)


def _read_batch_csv(path: Path) -> list[dict]:
    """Read input CSV for batch mode. Requires at least a name_en column."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "name_en" not in reader.fieldnames:
            return []
        for row in reader:
            if row.get("name_en", "").strip():
                rows.append(row)
    return rows


def _process_single_card_in_batch(
    page,
    card_name: str,
    collector_number: str | None,
    set_code: str | None,
    our_mid: str | None,
) -> dict:
    """Process a single card within an existing browser session for batch mode."""
    result = {
        "card_name": card_name,
        "collector_number": collector_number or "",
        "set_code": set_code or "",
        "edition_matched": False,
        "our_mid": our_mid or "",
        "liga_mid": "",
        "diff_pct": "",
        "status": "ERROR",
    }

    try:
        url = liga_url_for_card_name(card_name)
        response = page.goto(url, wait_until="networkidle", timeout=30000)

        if response and response.status == 404:
            result["status"] = "NOT_FOUND"
            print("  -> 404 Not Found")
            return result

        # Wait for price elements
        try:
            page.wait_for_selector('[class*="preco"], :text("R$")', timeout=8000)
        except Exception:
            page.wait_for_timeout(2000)

        html = page.content()

        # Edition selection
        editions = parse_edition_options(html)
        edition_selected = False

        if collector_number and editions:
            edition_value, matched = select_edition_from_matches(
                editions, collector_number, set_code
            )
            if matched and edition_value:
                try:
                    page.evaluate(f"editionsCard.changeEdition('{edition_value}')")
                    page.wait_for_timeout(2000)
                    try:
                        page.wait_for_selector("div.price-mkp div.price", timeout=5000)
                    except Exception:
                        pass
                    edition_selected = True
                    html = page.content()
                except Exception as e:
                    print(f"  -> Edition selection failed: {e}")

        result["edition_matched"] = edition_selected

        # Parse prices
        parsed = parse_card_prices(html, card_name)
        liga_mid = parsed["normal"].get("mid")

        if liga_mid:
            result["liga_mid"] = str(liga_mid)
            result["status"] = "OK"

            # Calculate diff_pct if we have our_mid
            if our_mid:
                try:
                    our_val = Decimal(str(our_mid).replace(",", "."))
                    liga_val = Decimal(str(liga_mid))
                    if our_val > 0:
                        diff = (liga_val - our_val) / our_val * 100
                        result["diff_pct"] = f"{diff:.1f}"
                        if abs(diff) > 50:
                            result["status"] = "BIG_DIFF"
                except (ValueError, ArithmeticError):
                    pass
        else:
            result["status"] = "NO_PRICE"

        mid_str = f"R$ {liga_mid}" if liga_mid else "N/A"
        print(
            f"  -> edition_matched={edition_selected}"
            f"  liga_mid={mid_str}  status={result['status']}"
        )

    except Exception as e:
        result["status"] = f"ERROR: {e}"
        print(f"  -> ERROR: {e}")

    return result


def _write_batch_csv(path: Path, results: list[dict]) -> None:
    """Write batch results to a CSV file."""
    fieldnames = [
        "card_name",
        "collector_number",
        "set_code",
        "edition_matched",
        "our_mid",
        "liga_mid",
        "diff_pct",
        "status",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def _print_batch_summary(results: list[dict]) -> None:
    """Print a summary of batch results to stdout."""
    total = len(results)
    edition_matched = sum(1 for r in results if r["edition_matched"])
    edition_not_matched = total - edition_matched
    price_found = sum(1 for r in results if r["liga_mid"])
    price_not_found = total - price_found
    big_diffs = sum(1 for r in results if r.get("diff_pct") and abs(float(r["diff_pct"])) > 50)
    errors = sum(1 for r in results if r["status"].startswith("ERROR"))

    print()
    print("=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)
    print(f"  Total processed:       {total}")
    print(f"  Edition matched:       {edition_matched}")
    print(f"  Edition NOT matched:   {edition_not_matched}")
    print(f"  Price found:           {price_found}")
    print(f"  Price NOT found:       {price_not_found}")
    print(f"  >50% deviation:        {big_diffs}")
    print(f"  Errors:                {errors}")
    print("=" * 60)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser. Separated for testability."""
    parser = argparse.ArgumentParser(description="Debug Liga Magic price parsing")
    parser.add_argument("card_name", nargs="?", help="Card name to search (single card mode)")
    parser.add_argument("--collector-number", "-cn", help="Collector number for edition selection")
    parser.add_argument(
        "--set-code",
        "-sc",
        help="Set code for edition disambiguation (e.g. cmm, fdn)",
    )
    parser.add_argument("--batch", "-b", help="CSV file path for batch mode")
    parser.add_argument("--limit", type=int, help="Max cards to process in batch mode")
    parser.add_argument("--no-headless", action="store_true", help="Show the browser window")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    if args.batch:
        run_batch(args.batch, limit=args.limit, headless=not args.no_headless)
    elif args.card_name:
        run_debug(
            args.card_name,
            args.collector_number,
            set_code=args.set_code,
            headless=not args.no_headless,
        )
    else:
        parser.error("Either provide a card_name or use --batch <csv_path>")
