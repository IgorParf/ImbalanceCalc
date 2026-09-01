"""Тести формул Порядку (глави 1–3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from imbalance_calc.config import CalculationSettings
from imbalance_calc.core.methodology import (
    SCENARIO_BASE,
    SCENARIO_DELTA,
    accounted_deviation,
    calculate_hourly,
    group_cost,
    participant_share,
)


class TestGroupCost:
    """Пункти 1.3 та 1.4 Порядку."""

    def test_surplus_uses_min_price(self):
        # W > 0: W * (P_DAM - min(P_DAM; IMSP) * (1 - K_im))
        cost = group_cost([10.0], [2000.0], [1500.0], 0.0)
        assert cost[0] == pytest.approx(10.0 * (2000.0 - 1500.0))

    def test_deficit_uses_max_price(self):
        # W < 0: |W| * (max(P_DAM; IMSP) * (1 + K_im) - P_DAM)
        cost = group_cost([-10.0], [2000.0], [3000.0], 0.0)
        assert cost[0] == pytest.approx(10.0 * (3000.0 - 2000.0))

    def test_zero_imbalance_costs_nothing(self):
        assert group_cost([0.0], [2000.0], [3000.0], 0.0)[0] == 0.0

    def test_price_coefficient_increases_deficit_cost(self):
        without = group_cost([-10.0], [2000.0], [3000.0], 0.0)[0]
        with_coefficient = group_cost([-10.0], [2000.0], [3000.0], 0.1)[0]
        assert with_coefficient > without

    def test_cost_is_never_negative(self):
        values = group_cost([-5.0, 5.0, 0.0], [2000.0] * 3, [10.0] * 3, 0.0)
        assert (values >= 0).all()


class TestAccountedDeviation:
    """Пункт 3.1 Порядку."""

    def _call(self, w_pr, w_f, d_w=0.0, k_e=5.0, alpha=100.0):
        settings = CalculationSettings(k_e=k_e, alpha=alpha)
        return accounted_deviation(
            pd.Series([w_pr]), pd.Series([w_f]), pd.Series([d_w]), settings
        )

    def test_deviation_below_threshold_is_not_billed(self):
        # 10 -> 9.6 це 4 % < 5 %
        w_alpha, billable = self._call(10.0, 9.6)
        assert w_alpha[0] == 0.0
        assert not billable[0]

    def test_deviation_exactly_at_threshold_is_not_billed(self):
        # Порівняння строге: рівно 5 % ще не тарифікується
        w_alpha, billable = self._call(10.0, 9.5)
        assert w_alpha[0] == 0.0
        assert not billable[0]

    def test_deviation_above_threshold_is_billed(self):
        w_alpha, billable = self._call(10.0, 9.0)
        assert billable[0]
        assert w_alpha[0] == pytest.approx(-1.0)

    def test_alpha_scales_result(self):
        w_alpha, _ = self._call(10.0, 9.0, alpha=50.0)
        assert w_alpha[0] == pytest.approx(-0.5)

    def test_zero_forecast_skips_threshold_check(self):
        w_alpha, billable = self._call(0.0, 0.001)
        assert billable[0]
        assert w_alpha[0] == pytest.approx(0.001)

    def test_delta_is_added_to_deviation(self):
        # Команди ОСП «повертають» невідпущений обсяг у відхилення
        w_alpha, _ = self._call(10.0, 2.0, d_w=8.0)
        assert w_alpha[0] == pytest.approx(0.0)


class TestParticipantShare:
    """Пункт 3.2 Порядку."""

    def _call(self, w_alpha, w_group, sum_sn, sum_sp, ieq_gb, p_dam=2000.0, imsp=3000.0):
        return participant_share(
            np.array([w_alpha]), np.array([w_group]), np.array([sum_sn]),
            np.array([sum_sp]), np.array([ieq_gb]), np.array([p_dam]),
            np.array([imsp]), 0.0,
        )[0]

    def test_deficit_branch(self):
        # частка -1/-100 від сальдо -50 МВт·год за ціною (3000 - 2000)
        value = self._call(-1.0, -50.0, -100.0, 40.0, -10.0)
        assert value == pytest.approx(abs(-1.0 / -100.0 * -50.0) * 1000.0)

    def test_surplus_branch(self):
        value = self._call(1.0, 50.0, -100.0, 40.0, 10.0, p_dam=2000.0, imsp=1500.0)
        assert value == pytest.approx(1.0 / 40.0 * 50.0 * 500.0)

    def test_opposite_signs_are_not_billed(self):
        # Учасник відхилився в інший бік, ніж група
        assert self._call(1.0, -50.0, -100.0, 40.0, -10.0) == 0.0

    def test_guaranteed_buyer_sign_matters(self):
        # Небаланс ГП протилежного знаку — платежу немає
        assert self._call(-1.0, -50.0, -100.0, 40.0, +10.0) == 0.0

    def test_zero_denominator_is_safe(self):
        assert self._call(-1.0, -50.0, 0.0, 40.0, -10.0) == 0.0


class TestScenarioSelection:
    """Глава 2, п. 2.1: погодинний вибір дешевшого сценарію."""

    def _frame(self, w_sum, w_sum_delta, imsp):
        return pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-07-01").date()],
                "hour": [1],
                "w_pr": [10.0], "w_f": [9.0], "d_w": [0.0],
                "imsp": [imsp], "p_dam": [2000.0],
                "w_s": [-1.0], "w_s_delta": [-1.0],
                "w_sum": [w_sum], "w_sum_delta": [w_sum_delta],
                "sum_w_sn": [-100.0], "sum_w_sp": [40.0],
                "sum_w_sn_delta": [-80.0], "sum_w_sp_delta": [40.0],
                "d_sum_w": [w_sum_delta - w_sum], "ieq_gb": [-50.0],
            }
        )

    def test_cheaper_base_scenario_wins(self):
        out = calculate_hourly(self._frame(-10.0, -100.0, 3000.0), CalculationSettings())
        assert out["scenario"][0] == SCENARIO_BASE
        assert out["w_group"][0] == -10.0

    def test_cheaper_delta_scenario_wins(self):
        out = calculate_hourly(self._frame(-100.0, -10.0, 3000.0), CalculationSettings())
        assert out["scenario"][0] == SCENARIO_DELTA
        assert out["w_group"][0] == -10.0

    def test_tie_keeps_base_scenario(self):
        out = calculate_hourly(self._frame(-10.0, -10.0, 3000.0), CalculationSettings())
        assert out["scenario"][0] == SCENARIO_BASE
