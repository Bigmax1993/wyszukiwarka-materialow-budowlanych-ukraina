"""Weryfikacja izolacji repo — brak plikow drugiej kampanii."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "pattern",
    [
        "pl_*.py",
        "tests/test_pl_*.py",
        ".github/workflows/pl_*.yml",
        ".github/workflows/sync-google-drive-pl.yml",
        "run_config/pl_*.json",
        "schedule/pl",
        "docs/PL_MATERIALY.md",
    ],
)
def test_no_pl_campaign_artifacts(pattern: str) -> None:
    matches = list(ROOT.glob(pattern))
    assert not matches, f"Znaleziono artefakty PL w repo UA: {matches}"
