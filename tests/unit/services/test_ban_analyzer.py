"""Tests for ban_analyzer service functions (F42)."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from src.services.ban_analyzer import (
    get_ban_summary,
    get_banned_collection_cards,
    get_card_legalities_with_changes,
)


@pytest.fixture()
def mock_repo():
    return MagicMock()


class TestGetBannedCollectionCards:
    def test_enriches_with_recently_changed(self, mock_repo):
        mock_repo.get_banned_collection_cards.return_value = [
            {
                "entry_id": 1,
                "card_id": 10,
                "name_en": "Counterspell",
                "name_pt": "Contrafeitico",
                "set_code": "DMR",
                "collector_number": "42",
                "quantity": 2,
                "format": "standard",
                "status": "banned",
                "effective_date": None,
            },
        ]
        mock_repo.get_recently_changed_card_ids.return_value = {10}

        results = get_banned_collection_cards(mock_repo, "u1")
        assert len(results) == 1
        assert results[0].recently_changed is True
        assert results[0].card_id == 10
        assert results[0].image_url is not None

    def test_not_recently_changed(self, mock_repo):
        mock_repo.get_banned_collection_cards.return_value = [
            {
                "entry_id": 1,
                "card_id": 10,
                "name_en": "Test",
                "name_pt": None,
                "set_code": "DMR",
                "collector_number": "1",
                "quantity": 1,
                "format": "standard",
                "status": "banned",
                "effective_date": None,
            },
        ]
        mock_repo.get_recently_changed_card_ids.return_value = set()

        results = get_banned_collection_cards(mock_repo, "u1")
        assert results[0].recently_changed is False

    def test_image_url_computed(self, mock_repo):
        mock_repo.get_banned_collection_cards.return_value = [
            {
                "entry_id": 1,
                "card_id": 10,
                "name_en": "Test",
                "name_pt": None,
                "set_code": "DMR",
                "collector_number": "42",
                "quantity": 1,
                "format": "standard",
                "status": "banned",
                "effective_date": None,
            },
        ]
        mock_repo.get_recently_changed_card_ids.return_value = set()

        results = get_banned_collection_cards(mock_repo, "u1")
        assert "scryfall.com" in results[0].image_url
        assert "42" in results[0].image_url

    def test_passes_format_filter(self, mock_repo):
        mock_repo.get_banned_collection_cards.return_value = []
        mock_repo.get_recently_changed_card_ids.return_value = set()

        get_banned_collection_cards(mock_repo, "u1", format_filter="modern")
        mock_repo.get_banned_collection_cards.assert_called_with("u1", "modern")


class TestGetBanSummary:
    def test_returns_correct_aggregate(self, mock_repo):
        mock_repo.get_collection_ban_summary.return_value = {
            "banned_count": 3,
            "restricted_count": 1,
        }
        mock_repo.get_recently_changed_card_ids.return_value = {10, 20}
        mock_repo.get_banned_collection_cards.return_value = [
            {
                "format": "standard",
                "card_id": 10,
                "entry_id": 1,
                "name_en": "",
                "name_pt": None,
                "set_code": "DMR",
                "collector_number": "1",
                "quantity": 1,
                "status": "banned",
                "effective_date": None,
            },
            {
                "format": "modern",
                "card_id": 20,
                "entry_id": 2,
                "name_en": "",
                "name_pt": None,
                "set_code": "DMR",
                "collector_number": "2",
                "quantity": 1,
                "status": "restricted",
                "effective_date": None,
            },
        ]

        result = get_ban_summary(mock_repo, "u1")
        assert result.banned_count == 3
        assert result.restricted_count == 1
        assert result.recently_changed_count == 2
        assert "modern" in result.formats_affected
        assert "standard" in result.formats_affected


class TestGetCardLegalitiesWithChanges:
    def test_sorts_by_status_priority(self, mock_repo):
        mock_repo.get_card_legalities_with_history.return_value = [
            {
                "format": "modern",
                "status": "legal",
                "effective_date": None,
                "recently_changed": False,
                "change_date": None,
                "old_status": None,
            },
            {
                "format": "standard",
                "status": "banned",
                "effective_date": None,
                "recently_changed": True,
                "change_date": datetime.now(),
                "old_status": "legal",
            },
            {
                "format": "vintage",
                "status": "restricted",
                "effective_date": None,
                "recently_changed": False,
                "change_date": None,
                "old_status": None,
            },
        ]

        results = get_card_legalities_with_changes(mock_repo, 1)
        assert len(results) == 3
        assert results[0].status == "banned"
        assert results[1].status == "restricted"
        assert results[2].status == "legal"

    def test_recently_changed_flag(self, mock_repo):
        mock_repo.get_card_legalities_with_history.return_value = [
            {
                "format": "standard",
                "status": "banned",
                "effective_date": date(2026, 1, 1),
                "recently_changed": True,
                "change_date": datetime(2026, 8, 20),
                "old_status": "legal",
            },
        ]

        results = get_card_legalities_with_changes(mock_repo, 1)
        assert results[0].recently_changed is True
        assert results[0].old_status == "legal"
