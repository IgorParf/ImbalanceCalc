"""Тести показників обмежень ОСП: тривалість і обмежений виробіток."""

from __future__ import annotations

import pandas as pd
import pytest

from imbalance_calc.core import calculate_settlement, curtailment_duration
from imbalance_calc.reporting import duration


class TestCurtailmentDuration:
    """Тривалість = ΔW / (факт + ΔW), бо файл ГП подає обсяг, а не час."""

    def _call(self, w_f: float, d_w: float) -> float:
        return float(curtailment_duration(pd.Series([w_f]), pd.Series([d_w]))[0])

    def test_no_curtailment_is_zero(self):
        assert self._call(5.0, 0.0) == 0.0

    def test_half_hour_curtailment(self):
        # Половина потенціалу втрачена -> півгодини
        assert self._call(5.0, 5.0) == pytest.approx(0.5)

    def test_real_example_from_july(self):
        # 05.07.2026, година 9: ΔW = 4,120 при фактичних 1,3842 МВт·год
        assert self._call(1.3842, 4.120) == pytest.approx(0.748519, abs=1e-6)

    def test_full_hour_when_nothing_generated(self):
        assert self._call(0.0, 8.0) == pytest.approx(1.0)

    def test_capped_at_one_hour(self):
        # Від'ємний факт (нічне споживання) не має давати понад годину
        assert self._call(-0.03, 8.0) <= 1.0

    def test_zero_potential_counts_as_full_hour(self):
        assert self._call(-2.0, 2.0) == pytest.approx(1.0)


class TestDurationFormat:
    def test_formats_hours_and_minutes(self):
        assert duration(33.8472) == "33 год 51 хв"

    def test_pads_minutes(self):
        assert duration(5.0) == "5 год 00 хв"

    def test_zero(self):
        assert duration(0.0) == "0 год 00 хв"


class TestAggregation:
    def test_month_total_equals_sum_of_hours(self, frame):
        result = calculate_settlement(frame)
        assert result.total_curtail_hours == pytest.approx(result.hours["curtail_hours"].sum())
        assert result.total_curtailed_mwh == pytest.approx(result.hours["d_w"].sum())

    def test_daily_totals_sum_to_month(self, frame):
        result = calculate_settlement(frame)
        assert result.daily["curtail_hours"].sum() == pytest.approx(result.total_curtail_hours)
        assert result.daily["curtailed_mwh"].sum() == pytest.approx(result.total_curtailed_mwh)

    def test_known_curtailment_totals(self, curtailed_frame):
        """0,5 + 0,25 + 1,0 год = 1 год 45 хв; обсяг 5 + 3 + 8 = 16 МВт·год."""
        result = calculate_settlement(curtailed_frame)
        assert result.total_curtail_hours == pytest.approx(1.75)
        assert duration(result.total_curtail_hours) == "1 год 45 хв"
        assert result.total_curtailed_mwh == pytest.approx(16.0)
        assert result.curtailed_periods == 3
        assert result.curtailed_days == 1

    def test_daily_table_has_curtailment_columns(self, frame):
        from imbalance_calc.reporting import daily_display

        columns = list(daily_display(calculate_settlement(frame)).columns)
        assert "Обмеження, год.хв" in columns
        assert "Обмежено виробіток, МВт·год" in columns

    def test_totals_rows_contain_curtailment(self, frame):
        from imbalance_calc.reporting import totals_rows

        labels = [label for label, _ in totals_rows(calculate_settlement(frame))]
        assert "Всього обмеження, год.хв" in labels
        assert "Всього обмежено виробіток, МВт·год" in labels
