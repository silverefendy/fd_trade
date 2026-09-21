import os
import unittest
from unittest.mock import MagicMock, patch

from fd_trade.utils.price_data import (
    calculate_market_regime,
    calculate_recommendation,
    get_nearest_level,
    get_volume_confirmation,
    round_to_tick,
)


class TestPriceData(unittest.TestCase):
    def test_nearest_level_all_categories(self):
        support = get_nearest_level(101, {"support_level": 100, "resistance_level": 115})
        resistance = get_nearest_level(114, {"support_level": 90, "resistance_level": 115})
        middle = get_nearest_level(100, {"support_level": 80, "resistance_level": 120})
        empty = get_nearest_level(100, {})
        self.assertEqual(support["category"], "mendekati support")
        self.assertEqual(resistance["category"], "mendekati resistance")
        self.assertEqual(middle["category"], "di tengah range")
        self.assertIsNone(empty["level_name"])

    def test_volume_categories_and_invalid_history(self):
        class Series:
            def __init__(self, values): self.values = values
            @property
            def empty(self): return not self.values
            def dropna(self): return self
            def __len__(self): return len(self.values)
            def __getitem__(self, key): return Series(self.values[key]) if isinstance(key, slice) else self.values[key]
            @property
            def iloc(self): return self
            def mean(self): return sum(self.values) / len(self.values)

        class History:
            empty = False
            def __init__(self, values): self.series = Series(values)
            def __contains__(self, key): return key == "Volume"
            def __getitem__(self, key): return self.series

        rows = lambda values: [{"volume": v} for v in values]  # baris Price History (dict)
        self.assertEqual(get_volume_confirmation("BBCA", rows([100] * 20 + [200]))["volume_status"], "Volume Tinggi")
        self.assertEqual(get_volume_confirmation("BBCA", rows([100] * 20 + [25]))["volume_status"], "Volume Rendah")
        self.assertEqual(get_volume_confirmation("BBCA", rows([100] * 21))["volume_status"], "Volume Normal")
        self.assertIsNone(get_volume_confirmation("BBCA", rows([100] * 20)))
        self.assertIsNone(get_volume_confirmation("BBCA", rows([0] * 21)))

    def test_recommendation_branches_and_notes(self):
        cases = [
            ("Bearish Kuat", 100, 90, 110, "Avoid"),
            ("Bullish Lemah", 101, 100, 110, "Buy"),
            ("Sideways", 109, 90, 110, "Sell"),
            ("Sideways", 100, 90, 120, "Wait"),
        ]
        for trend, price, support, resistance, expected in cases:
            result = calculate_recommendation("BBCA", price, trend, support, None, resistance)
            self.assertEqual(result["recommendation"], expected)
        result = calculate_recommendation(
            "BBCA", 101, "Bullish Lemah", 100, None, 110,
            ihsg_trend="Bearish Kuat", volume_status="Volume Rendah",
        )
        self.assertIn("IHSG sedang Bearish Kuat", result["notes"])
        self.assertIn("Volume Rendah", result["notes"])

    def test_market_regime_and_tick(self):
        self.assertEqual(calculate_market_regime("Bullish Kuat", 110, 100, 105), "Risk-On")
        self.assertEqual(calculate_market_regime("Bullish Lemah", 90, 100, 105), "Neutral")
        self.assertEqual(calculate_market_regime("Sideways"), "Neutral")
        self.assertEqual(calculate_market_regime("Bearish Lemah"), "Risk-Off")
        self.assertEqual(calculate_market_regime("Bearish Kuat"), "Avoid New Entry")
        self.assertEqual(round_to_tick(6503), 6500)

    @patch("fd_trade.utils.price_data.yf.Ticker")
    def test_mock_yfinance_current_price(self, ticker_class):
        class History:
            empty = False
            def __init__(self):
                self.close = MagicMock()
                self.close.iloc.__getitem__.return_value = 6500
            def __getitem__(self, key):
                return self.close

        close = MagicMock()
        close.iloc.__getitem__.return_value = 6500
        ticker_class.return_value.history.return_value = History()
        # A minimal mapping-shaped fake is enough for get_current_price's access pattern.
        from fd_trade.utils.price_data import get_current_price
        self.assertEqual(get_current_price("BBCA"), 6500.0)

    @unittest.skipUnless(os.getenv("FD_TRADE_TEST_LIVE") == "1", "FD_TRADE_TEST_LIVE bukan 1")
    def test_live_support_resistance_smoke(self):
        from fd_trade.utils.price_data import get_support_resistance
        try:
            result = get_support_resistance("TLKM")
        except Exception as exc:
            self.skipTest(f"Yahoo Finance tidak tersedia: {exc}")
        if not result:
            self.skipTest("Yahoo Finance tidak mengembalikan histori TLKM")
        self.assertIn("support_level", result)

    @unittest.skipUnless(os.getenv("FD_TRADE_TEST_LIVE") == "1", "FD_TRADE_TEST_LIVE bukan 1")
    def test_live_yfinance_smoke(self):
        from fd_trade.utils.price_data import get_current_price
        try:
            price = get_current_price("BBCA")
        except Exception as exc:
            self.skipTest(f"Yahoo Finance tidak tersedia: {exc}")
        if price is None:
            self.skipTest("Yahoo Finance tidak mengembalikan harga BBCA")
        self.assertGreater(price, 0)
