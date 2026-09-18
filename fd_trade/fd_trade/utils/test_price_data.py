import unittest

from fd_trade.utils.price_data import (
    calculate_market_regime,
    calculate_recommendation,
    get_nearest_level,
    get_volume_confirmation,
)


class FakeSeries:
    def __init__(self, values):
        self.values = values

    def dropna(self):
        return FakeSeries([value for value in self.values if value is not None])

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return FakeSeries(self.values[key])
        return self.values[key]

    @property
    def iloc(self):
        return self

    def mean(self):
        return sum(self.values) / len(self.values)


class FakeHistory:
    def __init__(self, volumes):
        self.volume = FakeSeries(volumes)
        self.empty = not volumes

    def __contains__(self, key):
        return key == "Volume"

    def __getitem__(self, key):
        return self.volume


class TestPriceData(unittest.TestCase):
    def test_nearest_level_support(self):
        result = get_nearest_level(101, {"support_level": 100, "resistance_level": 110})
        self.assertEqual(result["level_name"], "support_level")
        self.assertEqual(result["category"], "mendekati support")

    def test_nearest_level_resistance(self):
        result = get_nearest_level(109, {"support_level": 90, "resistance_level": 110})
        self.assertEqual(result["level_name"], "resistance_level")
        self.assertEqual(result["category"], "mendekati resistance")

    def test_nearest_level_middle_and_empty(self):
        middle = get_nearest_level(100, {"support_level": 80, "resistance_level": 120})
        empty = get_nearest_level(100, {})
        self.assertEqual(middle["category"], "di tengah range")
        self.assertIsNone(empty["level_name"])
        self.assertIsNone(empty["distance_pct"])

    def test_volume_confirmation_categories(self):
        history = FakeHistory([100] * 20 + [200])
        result = get_volume_confirmation("BBCA", history=history)
        self.assertEqual(result["volume_status"], "Volume Tinggi")
        history = FakeHistory([100] * 20 + [25])
        result = get_volume_confirmation("BBCA", history=history)
        self.assertEqual(result["volume_status"], "Volume Rendah")
        history = FakeHistory([100] * 21)
        result = get_volume_confirmation("BBCA", history=history)
        self.assertEqual(result["volume_status"], "Volume Normal")

    def test_volume_confirmation_insufficient_or_zero_baseline(self):
        short_history = FakeHistory([100] * 20)
        zero_history = FakeHistory([0] * 21)
        self.assertIsNone(get_volume_confirmation("BBCA", history=short_history))
        self.assertIsNone(get_volume_confirmation("BBCA", history=zero_history))

    def test_recommendation_ihsg_and_volume_notes(self):
        result = calculate_recommendation(
            "BBCA", 101, "Bullish Lemah", 100, None, 110,
            ihsg_trend="Bearish Kuat", volume_status="Volume Rendah",
        )
        self.assertEqual(result["recommendation"], "Buy")
        self.assertIn("IHSG sedang Bearish Kuat", result["notes"])
        self.assertIn("Volume Rendah", result["notes"])

    def test_sell_take_profit_levels(self):
        result = calculate_recommendation(
            "BBCA", 109, "Sideways", 90, 80, 110,
            resistance_level_2=120, resistance_level_3=130,
        )
        self.assertEqual(result["recommendation"], "Sell")
        self.assertEqual(result["take_profit_next"], 120)
        self.assertEqual(result["take_profit_extended"], 130)

    def test_market_regime_categories(self):
        self.assertEqual(calculate_market_regime("Bullish Kuat", 110, 100, 105), "Risk-On")
        self.assertEqual(calculate_market_regime("Bullish Lemah", 110, 100, 105), "Risk-On")
        self.assertEqual(calculate_market_regime("Sideways", 110, 100, 105), "Neutral")
        self.assertEqual(calculate_market_regime("Bearish Lemah", 90, 100, 105), "Risk-Off")
        self.assertEqual(calculate_market_regime("Bearish Kuat", 90, 100, 105), "Avoid New Entry")
