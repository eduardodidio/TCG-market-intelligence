from __future__ import annotations

from src.api.deps import get_db
from src.database.repository import Repository


def test_get_db_returns_repository():
    """get_db() generator yields a Repository instance."""
    gen = get_db()
    repo = next(gen)
    assert isinstance(repo, Repository)
