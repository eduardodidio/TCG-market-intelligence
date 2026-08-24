"""Tests for the collection matcher (F10-T02).

Covers test plan scenarios 8--14:
  8.  SKU exact match → matched / sku_exact
  9.  Name + set match → matched / name_set
 10.  Multiple name matches, no SKU → ambiguous
 11.  Empty search results → unmatched
 12.  Case-insensitive set code comparison
 13.  Collector numbers with letters
 14.  No SKU on results → name-based fallback
"""

from __future__ import annotations

from src.collection.matcher import CollectionEntry, MatchResult, match_collection_card
from src.domain.models import MypSearchResult

# ── fixtures ────────────────────────────────────────────────────


def _entry(
    set_code: str = "dmr",
    collector_number: str = "123",
    name_en: str = "Lightning Bolt",
    name_pt: str | None = None,
) -> CollectionEntry:
    return CollectionEntry(
        set_code=set_code,
        collector_number=collector_number,
        name_en=name_en,
        name_pt=name_pt,
    )


def _result(
    external_id: str = "1000",
    name: str = "Lightning Bolt",
    slug: str = "lightning-bolt",
    sku: str | None = "magic_dmr_123",
    set_code: str | None = "dmr",
    collector_number: str | None = "123",
    image_url: str | None = None,
) -> MypSearchResult:
    return MypSearchResult(
        external_id=external_id,
        name=name,
        slug=slug,
        url=f"https://mypcards.com/magic/produto/{external_id}/{slug}",
        sku=sku,
        set_code=set_code,
        collector_number=collector_number,
        image_url=image_url,
    )


# ── Test Plan Scenario 8: SKU exact match ───────────────────────


class TestSkuExactMatch:
    """Matcher returns status='matched', confidence='sku_exact' when a
    search result's parsed SKU matches the collection entry's
    set_code + collector_number."""

    def test_exact_sku_match(self):
        entry = _entry(set_code="dmr", collector_number="123")
        results = [_result(set_code="dmr", collector_number="123")]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"
        assert match.myp_result is results[0]
        assert match.candidates == results

    def test_sku_match_picks_correct_among_multiple(self):
        """When multiple results exist, SKU match finds the right one."""
        entry = _entry(set_code="ltr", collector_number="748")
        results = [
            _result(
                external_id="2000",
                name="Lightning Bolt",
                set_code="dmr",
                collector_number="123",
            ),
            _result(
                external_id="3000",
                name="Lightning Bolt",
                set_code="ltr",
                collector_number="748",
            ),
            _result(
                external_id="4000",
                name="Lightning Bolt",
                set_code="m21",
                collector_number="152",
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"
        assert match.myp_result is results[1]

    def test_sku_match_takes_priority_over_name_match(self):
        """SKU match must be prioritized over name matching."""
        entry = _entry(set_code="m21", collector_number="152", name_en="Lightning Bolt")
        results = [
            # Name matches but different set/number
            _result(
                external_id="1001",
                name="Lightning Bolt",
                set_code="dmr",
                collector_number="123",
            ),
            # SKU matches
            _result(
                external_id="1002",
                name="Relampago",  # different name!
                set_code="m21",
                collector_number="152",
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"
        assert match.myp_result is results[1]


# ── Test Plan Scenario 9: Name + set match ──────────────────────


class TestNameSetMatch:
    """Matcher returns status='matched', confidence='name_set' when name
    matches and set can be confirmed, but SKU is absent."""

    def test_name_and_set_match_no_sku(self):
        entry = _entry(set_code="dmr", collector_number="123", name_en="Lightning Bolt")
        results = [
            _result(
                external_id="5000",
                name="Lightning Bolt",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_set"
        assert match.myp_result is results[0]

    def test_name_set_match_among_multiple_names(self):
        """When multiple results match by name, the one with matching set wins."""
        entry = _entry(set_code="ltr", collector_number="20", name_en="Lightning Bolt")
        results = [
            _result(
                external_id="6000",
                name="Lightning Bolt",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
            _result(
                external_id="6001",
                name="Lightning Bolt",
                sku=None,
                set_code="ltr",
                collector_number=None,
            ),
            _result(
                external_id="6002",
                name="Lightning Bolt",
                sku=None,
                set_code="m21",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_set"
        assert match.myp_result is results[1]


# ── Test Plan Scenario 10: Ambiguous matches ────────────────────


class TestAmbiguousMatch:
    """Matcher returns status='ambiguous' when multiple candidates match
    by name but none match by set_code + collector_number."""

    def test_multiple_name_matches_no_sku_or_set(self):
        entry = _entry(set_code="m21", collector_number="152", name_en="Lightning Bolt")
        results = [
            _result(
                external_id="7000",
                name="Lightning Bolt",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
            _result(
                external_id="7001",
                name="Lightning Bolt",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "ambiguous"
        assert match.confidence == "none"
        assert match.myp_result is None
        assert match.candidates == results

    def test_multiple_name_matches_different_sets_none_matching(self):
        """Multiple name matches with set_codes, but none match the entry."""
        entry = _entry(set_code="m21", collector_number="152", name_en="Lightning Bolt")
        results = [
            _result(
                external_id="7100",
                name="Lightning Bolt",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
            _result(
                external_id="7101",
                name="Lightning Bolt",
                sku=None,
                set_code="ltr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "ambiguous"
        assert match.confidence == "none"
        assert match.myp_result is None


# ── Test Plan Scenario 11: Unmatched (empty results) ────────────


class TestUnmatched:
    """Matcher returns status='unmatched' when search results list is empty."""

    def test_empty_search_results(self):
        entry = _entry()
        match = match_collection_card(entry, [])

        assert match.status == "unmatched"
        assert match.confidence == "none"
        assert match.myp_result is None
        assert match.candidates == []

    def test_no_name_or_sku_overlap(self):
        """Results exist but none match by name or SKU."""
        entry = _entry(
            set_code="m21",
            collector_number="152",
            name_en="Lightning Bolt",
        )
        results = [
            _result(
                external_id="8000",
                name="Counterspell",
                sku="magic_dmr_64",
                set_code="dmr",
                collector_number="64",
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "unmatched"
        assert match.confidence == "none"
        assert match.myp_result is None
        assert match.candidates == results

    def test_entry_without_name_en_is_unmatched_if_no_sku_match(self):
        """Collection entry with no name_en falls to unmatched when SKU
        does not match."""
        entry = _entry(set_code="dmr", collector_number="999", name_en=None)
        results = [
            _result(
                external_id="8100",
                name="Something",
                set_code="dmr",
                collector_number="123",
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "unmatched"
        assert match.confidence == "none"


# ── Test Plan Scenario 12: Case-insensitive set_code ────────────


class TestCaseInsensitiveSetCode:
    """Set code comparison must be case-insensitive."""

    def test_lowercase_entry_uppercase_result(self):
        entry = _entry(set_code="dmr", collector_number="123")
        results = [_result(set_code="dmr", collector_number="123")]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"

    def test_uppercase_entry_lowercase_result(self):
        entry = _entry(set_code="DMR", collector_number="123")
        results = [_result(set_code="dmr", collector_number="123")]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"

    def test_mixed_case_entry_and_result(self):
        entry = _entry(set_code="Dmr", collector_number="123")
        results = [_result(set_code="dMR", collector_number="123")]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"

    def test_name_set_match_is_case_insensitive(self):
        """Name+set fallback also uses case-insensitive set comparison."""
        entry = _entry(set_code="ltr", name_en="Gandalf the Grey")
        results = [
            _result(
                external_id="9000",
                name="Gandalf the Grey",
                sku=None,
                set_code="ltr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_set"


# ── Test Plan Scenario 13: Collector numbers with letters ───────


class TestCollectorNumbersWithLetters:
    """Collector numbers like '123a' must match via string comparison."""

    def test_letter_suffix_matches(self):
        entry = _entry(set_code="dmr", collector_number="123a")
        results = [_result(set_code="dmr", collector_number="123a")]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"

    def test_letter_suffix_does_not_match_numeric_only(self):
        """'123a' must NOT match '123'."""
        entry = _entry(set_code="dmr", collector_number="123a")
        results = [_result(set_code="dmr", collector_number="123")]

        match = match_collection_card(entry, results)

        # SKU match fails, falls to name matching
        assert match.confidence != "sku_exact" or match.status != "matched"

    def test_numeric_does_not_match_letter_suffix(self):
        """'123' must NOT match '123b'."""
        entry = _entry(set_code="dmr", collector_number="123")
        results = [_result(set_code="dmr", collector_number="123b")]

        match = match_collection_card(entry, results)

        # Should fall to name matching since SKU number doesn't match
        assert match.confidence != "sku_exact" or match.status != "matched"


# ── Test Plan Scenario 14: No SKU → name fallback ──────────────


class TestNoSkuFallback:
    """When no search result has a SKU, matcher falls back to name matching."""

    def test_single_name_match_no_sku_no_set(self):
        """Single name match with no set info → name_only."""
        entry = _entry(set_code="dmr", collector_number="123", name_en="Lightning Bolt")
        results = [
            _result(
                external_id="10000",
                name="Lightning Bolt",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_only"
        assert match.myp_result is results[0]

    def test_all_results_lack_sku_but_one_name_and_set_matches(self):
        entry = _entry(set_code="ltr", collector_number="20", name_en="Gandalf the Grey")
        results = [
            _result(
                external_id="10100",
                name="Gandalf the Grey",
                sku=None,
                set_code="ltr",
                collector_number=None,
            ),
            _result(
                external_id="10101",
                name="Gandalf the White",
                sku=None,
                set_code="ltr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_set"
        assert match.myp_result is results[0]

    def test_name_comparison_is_case_insensitive(self):
        entry = _entry(name_en="LIGHTNING BOLT")
        results = [
            _result(
                external_id="10200",
                name="lightning bolt",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_only"

    def test_name_comparison_strips_whitespace(self):
        entry = _entry(name_en="  Lightning Bolt  ")
        results = [
            _result(
                external_id="10300",
                name="Lightning Bolt",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_only"


# ── Additional edge cases ───────────────────────────────────────


class TestEdgeCases:
    """Additional edge cases for robustness."""

    def test_match_result_dataclass_fields(self):
        """MatchResult has all required fields."""
        entry = _entry()
        result = MatchResult(
            status="matched",
            collection_entry=entry,
            myp_result=None,
            confidence="sku_exact",
            candidates=[],
        )
        assert result.status == "matched"
        assert result.collection_entry is entry
        assert result.myp_result is None
        assert result.confidence == "sku_exact"
        assert result.candidates == []

    def test_collection_entry_dataclass_defaults(self):
        """CollectionEntry has correct defaults."""
        entry = CollectionEntry(set_code="dmr", collector_number="1")
        assert entry.name_en is None

    def test_sku_match_with_no_name_en(self):
        """Entry with no name_en can still match by SKU."""
        entry = _entry(set_code="dmr", collector_number="123", name_en=None)
        results = [_result(set_code="dmr", collector_number="123")]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "sku_exact"

    def test_multiple_name_set_matches_is_ambiguous(self):
        """If multiple results match both name and set, result is ambiguous
        (since we cannot narrow further without collector_number)."""
        entry = _entry(set_code="dmr", collector_number="123", name_en="Lightning Bolt")
        results = [
            _result(
                external_id="11000",
                name="Lightning Bolt",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
            _result(
                external_id="11001",
                name="Lightning Bolt",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        # Two name+set matches with no SKU to disambiguate → ambiguous
        assert match.status == "ambiguous"
        assert match.confidence == "none"

    def test_split_card_name_no_match(self):
        """Split card with different MYP name format does not match."""
        entry = _entry(name_en="Fire // Ice")
        results = [
            _result(
                external_id="12000",
                name="Fire",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "unmatched"
        assert match.confidence == "none"


# ── F47: Portuguese name fallback matching ────────────────────


class TestNamePtMatching:
    """Matcher considers name_pt when matching by name."""

    def test_pt_name_matches_when_en_does_not(self):
        """Entry with name_pt matches a result whose name is the PT name."""
        entry = _entry(
            name_en="Lightning Bolt",
            name_pt="Relampago",
        )
        results = [
            _result(
                external_id="13000",
                name="Relampago",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_only"
        assert match.myp_result is results[0]

    def test_en_name_preferred_when_both_match(self):
        """When both EN and PT match different results, both are candidates.
        If exactly one matches name+set, that wins."""
        entry = _entry(
            set_code="dmr",
            name_en="Lightning Bolt",
            name_pt="Relampago",
        )
        results = [
            _result(
                external_id="13100",
                name="Lightning Bolt",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
            _result(
                external_id="13101",
                name="Relampago",
                sku=None,
                set_code="ltr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_set"
        assert match.myp_result is results[0]

    def test_name_pt_none_no_change(self):
        """When name_pt is None, matching behaves as before (EN only)."""
        entry = _entry(name_en="Lightning Bolt", name_pt=None)
        results = [
            _result(
                external_id="13200",
                name="Counterspell",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "unmatched"
        assert match.confidence == "none"

    def test_ambiguous_with_pt_and_en_matches(self):
        """Multiple name matches from both EN and PT names is ambiguous
        when none can be narrowed by set."""
        entry = _entry(
            set_code="m21",
            name_en="Lightning Bolt",
            name_pt="Relampago",
        )
        results = [
            _result(
                external_id="13300",
                name="Lightning Bolt",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
            _result(
                external_id="13301",
                name="Relampago",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "ambiguous"
        assert match.confidence == "none"

    def test_name_set_match_via_pt_name(self):
        """PT name + matching set_code yields name_set confidence."""
        entry = _entry(
            set_code="dmr",
            name_en="Lightning Bolt",
            name_pt="Relampago",
        )
        results = [
            _result(
                external_id="13400",
                name="Relampago",
                sku=None,
                set_code="dmr",
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_set"
        assert match.myp_result is results[0]

    def test_only_name_pt_no_name_en(self):
        """Entry with only name_pt (no name_en) can still match."""
        entry = CollectionEntry(
            set_code="dmr",
            collector_number="123",
            name_en=None,
            name_pt="Relampago",
        )
        results = [
            _result(
                external_id="13500",
                name="Relampago",
                sku=None,
                set_code=None,
                collector_number=None,
            ),
        ]

        match = match_collection_card(entry, results)

        assert match.status == "matched"
        assert match.confidence == "name_only"
