"""Тести локального сховища періодів у форматі parquet."""

from __future__ import annotations

import pytest

from imbalance_calc import store


@pytest.fixture
def tmp_store(tmp_path):
    return tmp_path / "store"


def test_round_trip_preserves_frame(frame, tmp_store):
    store.save_period(frame, "test.xlsx", "abc", directory=tmp_store)
    restored = store.load_period("2026-07", directory=tmp_store)
    assert restored.equals(frame)


def test_saved_period_metadata(frame, tmp_store):
    entry = store.save_period(frame, "липень.xlsx", "abc", directory=tmp_store)
    assert entry.period_key == "2026-07"
    assert entry.month_label == "липень 2026"
    assert entry.days == 2
    assert entry.hours == 48
    assert entry.source_name == "липень.xlsx"


def test_listing_is_newest_first(frame, tmp_store):
    store.save_period(frame, directory=tmp_store)
    june = frame.copy()
    june["date"] = june["date"].map(lambda d: d.replace(month=6))
    store.save_period(june, directory=tmp_store)
    assert [e.period_key for e in store.list_periods(tmp_store)] == ["2026-07", "2026-06"]


def test_resaving_replaces_period(frame, tmp_store):
    store.save_period(frame, "перший.xlsx", directory=tmp_store)
    store.save_period(frame, "другий.xlsx", directory=tmp_store)
    periods = store.list_periods(tmp_store)
    assert len(periods) == 1
    assert periods[0].source_name == "другий.xlsx"


def test_find_by_hash(frame, tmp_store):
    store.save_period(frame, "test.xlsx", "деякий-хеш", directory=tmp_store)
    assert store.find_by_hash("деякий-хеш", tmp_store).period_key == "2026-07"
    assert store.find_by_hash("інший", tmp_store) is None
    assert store.find_by_hash("", tmp_store) is None


def test_delete_period(frame, tmp_store):
    store.save_period(frame, directory=tmp_store)
    assert store.delete_period("2026-07", tmp_store)
    assert store.list_periods(tmp_store) == []
    assert not store.delete_period("2026-07", tmp_store)


def test_missing_period_raises(tmp_store):
    with pytest.raises(FileNotFoundError):
        store.load_period("2020-01", directory=tmp_store)


class TestPeriodKeys:
    def test_previous_period_within_year(self):
        assert store.previous_period_key("2026-07") == "2026-06"

    def test_previous_period_crosses_year(self):
        assert store.previous_period_key("2026-01") == "2025-12"

    def test_month_label(self):
        assert store.month_label_of("2026-01") == "січень 2026"


class TestComparisonCandidate:
    """Порівняння за замовчуванням — з попереднім місяцем."""

    def _seed(self, frame, tmp_store, months: list[int]) -> None:
        for month in months:
            shifted = frame.copy()
            shifted["date"] = shifted["date"].map(
                lambda d, m=month: d.replace(month=m)
            )
            store.save_period(shifted, directory=tmp_store)

    def test_previous_month_is_preferred(self, frame, tmp_store):
        self._seed(frame, tmp_store, [5, 6, 7])
        assert store.comparison_candidate("2026-07", tmp_store).period_key == "2026-06"

    def test_falls_back_to_nearest_earlier(self, frame, tmp_store):
        self._seed(frame, tmp_store, [4, 7])
        assert store.comparison_candidate("2026-07", tmp_store).period_key == "2026-04"

    def test_none_when_no_earlier_period(self, frame, tmp_store):
        self._seed(frame, tmp_store, [7, 8])
        assert store.comparison_candidate("2026-07", tmp_store) is None
