"""LigaMagic scraping feasibility spike.

Tests whether we can extract card prices from ligamagic.com.br
using Playwright browser automation.

Usage:
    python scripts/ligamagic_spike.py
"""

import asyncio
import re
import time

from playwright.async_api import async_playwright

CARDS_TO_TEST = [
    "Lightning Bolt",
    "Counterspell",
    "Sol Ring",
    "Thoughtseize",
    "Fatal Push",
]


async def test_card(page, card_name: str) -> dict:
    """Try to load a card page and extract price data."""
    url = (
        f"https://www.ligamagic.com.br/?view=cards/card"
        f"&card={card_name.replace(' ', '+')}&show=1"
    )
    start = time.monotonic()
    try:
        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        status = response.status if response else None

        # Wait for content to render (JS-heavy site)
        await page.wait_for_timeout(3000)

        title = await page.title()
        content = await page.content()
        elapsed = time.monotonic() - start

        # --- Extract price data using various strategies ---

        # Strategy 1: CSS selectors for price-like classes
        price_selectors = [
            '[class*="price"]',
            '[class*="preco"]',
            '[class*="valor"]',
            '[class*="Price"]',
            '[class*="Preco"]',
            '[class*="Valor"]',
            ".card-price",
            ".preco-card",
            "#preco",
            "#price",
        ]
        prices_by_selector = {}
        for sel in price_selectors:
            elements = await page.query_selector_all(sel)
            if elements:
                texts = []
                for el in elements:
                    text = await el.text_content()
                    if text and text.strip():
                        texts.append(text.strip()[:200])
                if texts:
                    prices_by_selector[sel] = texts[:5]

        # Strategy 2: Regex for R$ patterns in body text
        body_text = await page.inner_text("body")
        price_pattern = re.findall(r"R\$\s*[\d.,]+", body_text)

        # Strategy 3: Look for table rows with price data
        table_rows = await page.query_selector_all("table tr")
        table_data = []
        for row in table_rows[:20]:
            text = await row.text_content()
            if text and "R$" in text:
                table_data.append(text.strip()[:300])

        # Strategy 4: Look for specific LigaMagic elements
        liga_selectors = {
            "#card-name": None,
            ".card-name": None,
            "#card-image": None,
            ".card-image": None,
            ".edition-name": None,
            ".store-name": None,
            ".loja": None,
        }
        for sel in liga_selectors:
            el = await page.query_selector(sel)
            if el:
                liga_selectors[sel] = (await el.text_content() or "").strip()[:200]
        found_elements = {k: v for k, v in liga_selectors.items() if v}

        # Strategy 5: Check for captcha / anti-bot
        captcha_indicators = []
        for indicator in ["captcha", "recaptcha", "hcaptcha", "cloudflare", "challenge"]:
            if indicator in content.lower():
                captcha_indicators.append(indicator)

        # Strategy 6: Check for login / auth walls
        auth_indicators = []
        for indicator in ["login", "entrar", "cadastr", "signin"]:
            count = content.lower().count(indicator)
            if count > 0:
                auth_indicators.append(f"{indicator}({count})")

        return {
            "card": card_name,
            "url": url,
            "status": status,
            "title": title,
            "elapsed_seconds": round(elapsed, 2),
            "page_length": len(content),
            "prices_by_selector": prices_by_selector,
            "prices_by_regex": price_pattern[:15],
            "table_price_rows": table_data[:5],
            "found_elements": found_elements,
            "captcha_indicators": captcha_indicators,
            "auth_indicators": auth_indicators,
            "success": bool(price_pattern),
            "body_snippet": body_text[:500] if body_text else "",
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "card": card_name,
            "url": url,
            "error": str(e),
            "elapsed_seconds": round(elapsed, 2),
            "success": False,
        }


async def main():
    print("=" * 70)
    print("LigaMagic Scraping Feasibility Spike")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
        )
        page = await context.new_page()

        results = []
        for i, card in enumerate(CARDS_TO_TEST):
            print(f"\n[{i + 1}/{len(CARDS_TO_TEST)}] Testing: {card}...")
            result = await test_card(page, card)
            results.append(result)

            print(f"  HTTP Status: {result.get('status', 'N/A')}")
            print(f"  Page Title:  {result.get('title', 'N/A')}")
            print(f"  Page Size:   {result.get('page_length', 0):,} bytes")
            print(f"  Time:        {result.get('elapsed_seconds', '?')}s")
            print(f"  Success:     {result.get('success', False)}")

            if result.get("prices_by_regex"):
                print(f"  Prices (regex): {result['prices_by_regex'][:5]}")
            if result.get("prices_by_selector"):
                for sel, vals in result["prices_by_selector"].items():
                    print(f"  Prices ({sel}): {vals[:3]}")
            if result.get("table_price_rows"):
                print(f"  Table rows with R$: {len(result['table_price_rows'])}")
                for row in result["table_price_rows"][:2]:
                    print(f"    -> {row[:120]}")
            if result.get("found_elements"):
                print(f"  Found elements: {result['found_elements']}")
            if result.get("captcha_indicators"):
                print(f"  CAPTCHA detected: {result['captcha_indicators']}")
            if result.get("auth_indicators"):
                print(f"  Auth indicators: {result['auth_indicators']}")
            if result.get("error"):
                print(f"  ERROR: {result['error']}")

            # Body snippet for first card only (for debugging)
            if i == 0 and result.get("body_snippet"):
                print(f"  Body snippet: {result['body_snippet'][:300]}...")

            # Rate limit: wait 4 seconds between requests
            if i < len(CARDS_TO_TEST) - 1:
                print("  (waiting 4s...)")
                await asyncio.sleep(4)

        await browser.close()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    successes = sum(1 for r in results if r.get("success"))
    avg_time = sum(r.get("elapsed_seconds", 0) for r in results) / len(results)
    print(f"Cards tested:    {len(results)}")
    print(f"Successful:      {successes}/{len(results)}")
    print(f"Avg time/card:   {avg_time:.2f}s")
    print(f"Captcha issues:  {sum(1 for r in results if r.get('captcha_indicators'))}")
    print(f"Auth walls:      {sum(1 for r in results if r.get('auth_indicators'))}")
    print()

    if successes >= 3:
        print("VERDICT: GO -- LigaMagic scraping is feasible")
    elif successes >= 1:
        print("VERDICT: PARTIAL -- LigaMagic scraping works but is unreliable")
    else:
        print("VERDICT: NO-GO -- LigaMagic scraping is not feasible")

    return results


if __name__ == "__main__":
    asyncio.run(main())
