"""End-to-end test: real DART API call, real ZIP download, real parse.

Marked e2e — run explicitly with `uv run pytest -m e2e`. Requires a valid
DART_API_KEY in .env. Free quota usage (1 of 20,000 daily calls).
"""

import pytest

from k_fingraph.config import get_settings
from k_fingraph.sources.dart import fetch_corp_codes


@pytest.mark.e2e
def test_fetch_corp_codes_returns_full_corpus() -> None:
    # Skip cleanly if no key is configured (e.g. CI without secrets).
    try:
        get_settings()
    except Exception as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"DART_API_KEY not configured: {exc}")

    records = fetch_corp_codes()

    # DART's corpCode currently registers ~100k entities; assert a generous lower bound.
    assert len(records) >= 80_000, f"expected >= 80k records, got {len(records)}"

    # Sanity: a well-known listed company should appear with the expected stock_code.
    by_code = {r.corp_code: r for r in records}
    samsung = by_code.get("00126380")
    assert samsung is not None, "Samsung Electronics (00126380) missing from corpCode"
    assert samsung.stock_code == "005930"
    assert "삼성전자" in samsung.corp_name
