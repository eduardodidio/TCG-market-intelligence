"""Compare Liga Magic collection HTML exports with our stored prices.

Usage:
    python scripts/liga_collection_compare.py

Reads all HTML files from docs/htmlsColecao/ (saved via Ctrl+S from Liga),
parses card names + prices, compares with our database, and generates
a discrepancy report.

Output:
    scripts/debug_output/collection_data.json   — parsed cards from Liga HTML
    scripts/debug_output/price_comparison.csv    — full comparison report
    scripts/debug_output/mismatches.csv          — only cards with >20% diff
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUT_DIR = Path(__file__).parent / "debug_output"
OUTPUT_DIR.mkdir(exist_ok=True)

HTML_DIR = Path(__file__).resolve().parent.parent / "docs" / "htmlsColecao"


def normalize_diacritics(text: str) -> str:
    """Strip diacritical marks from text.

    Uses NFKD normalization to decompose characters, then removes
    combining characters (accents, umlauts, circumflexes, etc.).

    Examples:
        "Dáin" -> "Dain"
        "Andúril" -> "Anduril"
        "Barad-dûr" -> "Barad-dur"
        "Sméagol" -> "Smeagol"
    """
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def classify_hint(
    name_en: str,
    extras: str | None,
    edition: str | None,
    liga_buy: Decimal | None,
    diff_pct: float | None,
) -> str:
    """Classify a mismatch into a root-cause hint category.

    Returns the first matching hint, checked in priority order:
        foil_card   - extras contains "Foil"
        dfc_card    - name contains " // "
        art_card    - edition contains "Art Series" or name contains "Art Card"
        promo       - extras contains "Promo" or "Pre Release"
        variant_ed  - edition contains variant keywords
        cheap_card  - Liga buy price < R$1.00
        expected    - positive diff AND no other hint AND Liga > R$5
        (empty)     - no hint applies
    """
    extras_str = extras or ""
    edition_str = edition or ""

    if "Foil" in extras_str:
        return "foil_card"

    if " // " in (name_en or ""):
        return "dfc_card"

    if "Art Series" in edition_str or "Art Card" in (name_en or ""):
        return "art_card"

    if "Promo" in extras_str or "Pre Release" in extras_str:
        return "promo"

    variant_keywords = ["(Variantes)", "(Borderless)", "(Extended Art)", "(Showcase)", "(Retro)"]
    if any(kw in edition_str for kw in variant_keywords):
        return "variant_ed"

    if liga_buy is not None and liga_buy < Decimal("1.00"):
        return "cheap_card"

    # "expected" = our price is higher (positive diff) and Liga price > R$5
    if (
        diff_pct is not None
        and diff_pct > 0
        and liga_buy is not None
        and liga_buy > Decimal("5.00")
    ):
        return "expected"

    return ""


def _parse_brl(text: str) -> Decimal | None:
    """Parse 'R$ 1.234,56' into Decimal."""
    if not text:
        return None
    cleaned = re.sub(r"R\$\s*", "", text.strip())
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_liga_collection_html(html: str) -> list[dict]:
    """Extract cards from a Liga Magic collection HTML page.

    Each card row: <tr class="pointer" id="cc_card_{liga_card_id}_{edition_id}">
    Contains: quantity, collector_number, edition, card_name (PT+EN), extras,
    language, quality, rarity, color, buy_price, sell_price.
    """
    cards = []

    # Find all card rows
    row_pattern = re.compile(
        r'<tr\s+class="pointer"\s+id="cc_card_(\d+)_(\d+)">(.*?)</tr>',
        re.DOTALL,
    )

    for match in row_pattern.finditer(html):
        liga_card_id = match.group(1)
        edition_id = match.group(2)
        row_html = match.group(3)

        # Quantity
        qty_match = re.search(r"<b>(\d+)x</b>", row_html)
        quantity = int(qty_match.group(1)) if qty_match else 1

        # Collector number
        cn_match = re.search(r'<td\s+class="f9">\s*#(\w+)\s*</td>', row_html)
        collector_number = cn_match.group(1).strip() if cn_match else None

        # Edition name (from img title in col-ed-txt)
        ed_match = re.search(r'class="col-ed-txt"[^>]*title="([^"]*)"', row_html)
        edition_name = ed_match.group(1) if ed_match else None

        # Card names — extract from links
        # PT name is usually first, EN name second (italic, smaller)
        name_links = re.findall(
            r'<a\s+href="[^"]*\?view=cards/card[^"]*"[^>]*>([^<]+)</a>',
            row_html,
        )
        name_pt = name_links[0].strip() if len(name_links) >= 1 else None
        name_en = name_links[1].strip() if len(name_links) >= 2 else name_pt

        # Card URL (from the first card link)
        url_match = re.search(
            r'href="(https://www\.ligamagic\.com\.br/\?view=cards/card[^"]*)"',
            row_html,
        )
        card_url = url_match.group(1) if url_match else None

        # Extras (Foil, Promo, etc.) — find the <td class="f9"> that contains Foil/Promo text
        # It's the td after the card name td, before the language flag
        extras = None
        # Find all f9 tds and look for ones with Foil/Promo content
        f9_tds = re.findall(r'<td\s+class="f9">(.*?)</td>', row_html, re.DOTALL)
        for td_content in f9_tds:
            clean = re.sub(r"<[^>]+>", "", td_content).strip()
            if clean and any(
                kw in clean for kw in ["Foil", "Promo", "Etched", "Showcase", "Extended"]
            ):
                extras = clean
                break

        # Buy price (col-pcompra)
        buy_match = re.search(r'class="col-pcompra"[^>]*>(R\$[^<]+)', row_html)
        buy_price = _parse_brl(buy_match.group(1)) if buy_match else None

        # Sell price (col-pvenda)
        sell_match = re.search(r'class="col-pvenda"[^>]*>(R\$[^<]+)', row_html)
        sell_price = _parse_brl(sell_match.group(1)) if sell_match else None

        cards.append(
            {
                "liga_card_id": liga_card_id,
                "edition_id": edition_id,
                "quantity": quantity,
                "collector_number": collector_number,
                "edition_name": edition_name,
                "name_pt": name_pt,
                "name_en": name_en,
                "card_url": card_url,
                "extras": extras,
                "buy_price": str(buy_price) if buy_price else None,
                "sell_price": str(sell_price) if sell_price else None,
            }
        )

    return cards


def load_all_pages() -> list[dict]:
    """Parse all HTML files from the collection export directory."""
    all_cards = []
    html_files = sorted(HTML_DIR.glob("*.html"))

    if not html_files:
        print(f"No HTML files found in {HTML_DIR}")
        return []

    for html_file in html_files:
        print(f"Parsing: {html_file.name}")
        html = html_file.read_text(encoding="utf-8")
        cards = parse_liga_collection_html(html)
        print(f"  Found {len(cards)} cards")
        all_cards.extend(cards)

    # Deduplicate by liga_card_id + edition_id
    seen = set()
    unique = []
    for c in all_cards:
        key = f"{c['liga_card_id']}_{c['edition_id']}"
        if key not in seen:
            seen.add(key)
            unique.append(c)

    print(f"\nTotal unique cards: {len(unique)}")
    return unique


def compare_with_db(liga_cards: list[dict]) -> list[dict]:
    """Compare Liga collection prices with our database prices."""
    from sqlalchemy import text

    from src.config import get_db_url
    from src.database.repository import Repository

    repo = Repository(get_db_url())
    results = []

    with repo.engine.connect() as conn:
        for card in liga_cards:
            liga_buy = Decimal(card["buy_price"]) if card.get("buy_price") else None
            name_en = card.get("name_en") or card.get("name_pt") or "?"
            name_pt = card.get("name_pt", "")

            # Try to find in our collection by name_en (fuzzy match)
            row = conn.execute(
                text("""
                    SELECT uc.card_id, uc.name_en, uc.name_pt,
                           uc.collector_number, uc.extras, uc.set_code
                    FROM user_collection uc
                    WHERE (uc.name_en ILIKE :name_en OR uc.name_pt ILIKE :name_pt)
                      AND uc.collector_number = :cn
                    LIMIT 1
                """),
                {
                    "name_en": f"%{name_en}%",
                    "name_pt": f"%{name_pt}%",
                    "cn": card.get("collector_number", ""),
                },
            ).fetchone()

            # Fallback: match by name only (no collector_number constraint)
            if not row:
                row = conn.execute(
                    text("""
                        SELECT uc.card_id, uc.name_en, uc.name_pt,
                               uc.collector_number, uc.extras, uc.set_code
                        FROM user_collection uc
                        WHERE uc.name_en ILIKE :name_en OR uc.name_pt ILIKE :name_pt
                        LIMIT 1
                    """),
                    {
                        "name_en": f"%{name_en}%",
                        "name_pt": f"%{name_pt}%",
                    },
                ).fetchone()

            # Fallback: normalized diacritics match (handles Dáin, Andúril, etc.)
            if not row:
                norm_en = normalize_diacritics(name_en)
                norm_pt = normalize_diacritics(name_pt)
                # Only attempt if normalization actually changed something
                if norm_en != name_en or norm_pt != name_pt:
                    row = conn.execute(
                        text("""
                            SELECT uc.card_id, uc.name_en, uc.name_pt,
                                   uc.collector_number, uc.extras, uc.set_code
                            FROM user_collection uc
                            WHERE (uc.name_en ILIKE :name_en OR uc.name_pt ILIKE :name_pt)
                              AND uc.collector_number = :cn
                            LIMIT 1
                        """),
                        {
                            "name_en": f"%{norm_en}%",
                            "name_pt": f"%{norm_pt}%",
                            "cn": card.get("collector_number", ""),
                        },
                    ).fetchone()

                    # Normalized match without collector_number
                    if not row:
                        row = conn.execute(
                            text("""
                                SELECT uc.card_id, uc.name_en, uc.name_pt,
                                       uc.collector_number, uc.extras, uc.set_code
                                FROM user_collection uc
                                WHERE uc.name_en ILIKE :name_en
                                   OR uc.name_pt ILIKE :name_pt
                                LIMIT 1
                            """),
                            {
                                "name_en": f"%{norm_en}%",
                                "name_pt": f"%{norm_pt}%",
                            },
                        ).fetchone()

            if not row:
                results.append(
                    {
                        "name_en": name_en,
                        "name_pt": card.get("name_pt", ""),
                        "collector_number": card.get("collector_number"),
                        "edition": card.get("edition_name", ""),
                        "extras": card.get("extras", ""),
                        "liga_buy_price": card.get("buy_price", "N/A"),
                        "our_price": "NOT_IN_DB",
                        "diff": "N/A",
                        "diff_pct": "N/A",
                        "card_id": None,
                        "status": "NOT_IN_DB",
                        "hint": "",
                    }
                )
                continue

            d = dict(row._mapping)
            card_id = d["card_id"]

            # Get our latest Liga price
            eid_normal = f"liga_{card_id}"
            eid_foil = f"liga_{card_id}_foil"
            price_row = conn.execute(
                text("""
                    SELECT median_price, external_id, observed_at
                    FROM price_observations
                    WHERE external_id IN (:eid_n, :eid_f)
                    ORDER BY observed_at DESC
                    LIMIT 1
                """),
                {"eid_n": eid_normal, "eid_f": eid_foil},
            ).fetchone()

            our_price = Decimal(str(price_row._mapping["median_price"])) if price_row else None
            observed_at = str(price_row._mapping["observed_at"]) if price_row else None

            diff = None
            diff_pct = None
            status = "OK"

            if liga_buy and our_price:
                diff = our_price - liga_buy
                if liga_buy > 0:
                    diff_pct = float(diff / liga_buy * 100)
                abs_pct = abs(diff_pct or 0)
                is_above = (diff_pct or 0) > 0
                if abs_pct > 50:
                    status = "BIG_ABOVE" if is_above else "BIG_BELOW"
                elif abs_pct > 20:
                    status = "MISMATCH_ABOVE" if is_above else "MISMATCH_BELOW"
                elif abs_pct > 5:
                    status = "DRIFT"
            elif liga_buy and not our_price:
                status = "NO_OUR_PRICE"
            elif not liga_buy:
                status = "NO_LIGA_PRICE"

            result_name_en = d.get("name_en") or name_en
            hint = classify_hint(
                name_en=result_name_en,
                extras=card.get("extras"),
                edition=card.get("edition_name"),
                liga_buy=liga_buy,
                diff_pct=diff_pct,
            )

            results.append(
                {
                    "name_en": result_name_en,
                    "name_pt": card.get("name_pt", ""),
                    "collector_number": card.get("collector_number"),
                    "edition": card.get("edition_name", ""),
                    "extras": card.get("extras", ""),
                    "liga_buy_price": card.get("buy_price", "N/A"),
                    "our_price": str(our_price) if our_price else "N/A",
                    "observed_at": observed_at or "N/A",
                    "diff": f"{diff:.2f}" if diff is not None else "N/A",
                    "diff_pct": f"{diff_pct:+.1f}%" if diff_pct is not None else "N/A",
                    "card_id": card_id,
                    "status": status,
                    "hint": hint,
                }
            )

    return results


def save_reports(results: list[dict]):
    """Save comparison results as CSV + print summary."""
    fields = [
        "status",
        "hint",
        "name_en",
        "name_pt",
        "collector_number",
        "edition",
        "extras",
        "liga_buy_price",
        "our_price",
        "diff",
        "diff_pct",
        "observed_at",
        "card_id",
    ]

    # Full report
    csv_path = OUTPUT_DIR / "price_comparison.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in sorted(results, key=lambda x: x["status"]):
            writer.writerow(r)
    print(f"\nFull report: {csv_path}")

    # Mismatches only
    mismatch_statuses = (
        "MISMATCH_ABOVE",
        "MISMATCH_BELOW",
        "BIG_ABOVE",
        "BIG_BELOW",
    )
    mismatches = [r for r in results if r["status"] in mismatch_statuses]
    if mismatches:
        mm_path = OUTPUT_DIR / "mismatches.csv"
        with open(mm_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in sorted(
                mismatches,
                key=lambda x: abs(float(x["diff_pct"].rstrip("%").replace("+", "")))
                if x["diff_pct"] != "N/A"
                else 0,
                reverse=True,
            ):
                writer.writerow(r)
        print(f"Mismatches: {mm_path}")

    # Summary
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "OK")
    drift = sum(1 for r in results if r["status"] == "DRIFT")
    mm_above = sum(1 for r in results if r["status"] == "MISMATCH_ABOVE")
    mm_below = sum(1 for r in results if r["status"] == "MISMATCH_BELOW")
    big_above = sum(1 for r in results if r["status"] == "BIG_ABOVE")
    big_below = sum(1 for r in results if r["status"] == "BIG_BELOW")
    no_our = sum(1 for r in results if r["status"] == "NO_OUR_PRICE")
    no_liga = sum(1 for r in results if r["status"] == "NO_LIGA_PRICE")
    not_in_db = sum(1 for r in results if r["status"] == "NOT_IN_DB")

    print(f"\n{'='*65}")
    print("COMPARISON SUMMARY (Liga 'Menor Compra' vs Our 'Mid')")
    print(f"{'='*65}")
    print(f"Total cards from Liga:     {total}")
    print(f"  OK (< 5% diff):          {ok}")
    print(f"  DRIFT (5-20%):           {drift}")
    print(f"  MISMATCH_ABOVE (20-50%): {mm_above}")
    print(f"  MISMATCH_BELOW (20-50%): {mm_below}")
    print(f"  BIG_ABOVE (> 50%):       {big_above}")
    print(f"  BIG_BELOW (> 50%):       {big_below}")
    print(f"  No price in our DB:      {no_our}")
    print(f"  No Liga price:           {no_liga}")
    print(f"  Not found in our DB:     {not_in_db}")
    print(f"{'='*65}")

    # Note about price types
    print("\nNOTE: Liga shows 'Menor Preco de Compra' (lowest buy price)")
    print("      Our DB stores 'mid' (market median price)")
    print("      Our price is expected to be HIGHER than Liga's lowest.")
    print("      Focus on BIG_BELOW and MISMATCH_BELOW (our price < Liga).")

    # Hint breakdown for mismatches
    hint_counts: dict[str, int] = {}
    for r in results:
        if r["status"] in mismatch_statuses:
            h = r.get("hint", "") or "(no hint)"
            hint_counts[h] = hint_counts.get(h, 0) + 1

    if hint_counts:
        print(f"\n{'='*65}")
        print("MISMATCH ROOT-CAUSE HINTS")
        print(f"{'='*65}")
        for hint_name, count in sorted(hint_counts.items(), key=lambda x: -x[1]):
            print(f"  {hint_name:20s}  {count}")

    if big_above + big_below > 0:
        print("\nBIGGEST MISMATCHES (>50% diff):")
        bm = [r for r in results if r["status"] in ("BIG_ABOVE", "BIG_BELOW")]
        bm.sort(
            key=lambda x: abs(float(x["diff_pct"].rstrip("%").replace("+", "")))
            if x["diff_pct"] != "N/A"
            else 0,
            reverse=True,
        )
        for r in bm[:20]:
            hint_tag = f"  [{r['hint']}]" if r.get("hint") else ""
            print(
                f"  {r['name_en']:40s}  Liga={r['liga_buy_price']:>10s}"
                f"  Ours={r['our_price']:>10s}  ({r['diff_pct']:>7s})"
                f"  {r['extras'] or ''}{hint_tag}"
            )

    if mm_above + mm_below > 0:
        print("\nMISMATCHES (20-50% diff):")
        mm = [r for r in results if r["status"] in ("MISMATCH_ABOVE", "MISMATCH_BELOW")]
        mm.sort(
            key=lambda x: abs(float(x["diff_pct"].rstrip("%").replace("+", "")))
            if x["diff_pct"] != "N/A"
            else 0,
            reverse=True,
        )
        for r in mm[:20]:
            hint_tag = f"  [{r['hint']}]" if r.get("hint") else ""
            print(
                f"  {r['name_en']:40s}  Liga={r['liga_buy_price']:>10s}"
                f"  Ours={r['our_price']:>10s}  ({r['diff_pct']:>7s})"
                f"  {r['extras'] or ''}{hint_tag}"
            )


if __name__ == "__main__":
    print("Step 1: Parse Liga collection HTML files")
    print("-" * 45)
    liga_cards = load_all_pages()

    if not liga_cards:
        print(f"\nNo cards found. Make sure HTML files are in {HTML_DIR}/")
        sys.exit(1)

    # Save raw extraction
    data_path = OUTPUT_DIR / "collection_data.json"
    data_path.write_text(
        json.dumps(liga_cards, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Raw data saved: {data_path}")

    print("\nStep 2: Compare with our database")
    print("-" * 45)
    results = compare_with_db(liga_cards)
    save_reports(results)
