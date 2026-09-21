import datetime
import unittest

from fd_trade.utils.pattern_detection import detect_chart_patterns


def make_rows(closes, volume=1000):
    start = datetime.date(2026, 1, 1)
    return [
        {"date": (start + datetime.timedelta(days=index)).isoformat(), "open": value,
         "high": value + 1, "low": value - 1, "close": value, "volume": volume}
        for index, value in enumerate(closes)
    ]


class TestPatternDetection(unittest.TestCase):
    def assert_pattern(self, closes, name, direction, confidence="confirmed"):
        results = detect_chart_patterns(make_rows(closes), lookback_days=90)
        matches = [item for item in results if item["pattern_name"] == name]
        self.assertTrue(matches, f"{name} tidak terdeteksi: {results}")
        self.assertEqual(matches[0]["direction"], direction)
        self.assertEqual(matches[0]["confidence_level"], confidence)

    def test_double_bottom(self):
        closes = [100] * 35
        closes[5], closes[14], closes[25], closes[-1] = 90, 110, 92, 100
        self.assert_pattern(closes, "Double Bottom", "Bullish", confidence="tentative")

    def test_double_top(self):
        closes = [100] * 35
        closes[5], closes[14], closes[25], closes[-1] = 110, 90, 108, 100
        self.assert_pattern(closes, "Double Top", "Bearish", confidence="tentative")

    def test_inverse_head_and_shoulders(self):
        closes = [100] * 35
        closes[5], closes[10], closes[16], closes[22], closes[27], closes[-1] = 90, 105, 75, 105, 91, 102
        self.assert_pattern(closes, "Inverse Head and Shoulders", "Bullish", confidence="tentative")

    def test_head_and_shoulders(self):
        closes = [100] * 35
        closes[5], closes[10], closes[16], closes[22], closes[27], closes[-1] = 110, 95, 125, 95, 109, 98
        self.assert_pattern(closes, "Head and Shoulders", "Bearish", confidence="tentative")

    # --- CONFIRMED: close terakhir sudah menembus neckline (perbaikan 19 Sep 2026) ---
    def test_double_bottom_confirmed_after_neckline_break(self):
        closes = [100] * 35
        closes[5], closes[14], closes[25], closes[-1] = 90, 110, 92, 113
        self.assert_pattern(closes, "Double Bottom", "Bullish", confidence="confirmed")

    def test_double_top_confirmed_after_neckline_break(self):
        closes = [100] * 35
        closes[5], closes[14], closes[25], closes[-1] = 110, 90, 108, 87
        self.assert_pattern(closes, "Double Top", "Bearish", confidence="confirmed")

    def test_inverse_head_and_shoulders_confirmed_after_neckline_break(self):
        closes = [100] * 35
        closes[5], closes[10], closes[16], closes[22], closes[27], closes[-1] = 90, 105, 75, 105, 91, 109
        self.assert_pattern(closes, "Inverse Head and Shoulders", "Bullish", confidence="confirmed")

    def test_head_and_shoulders_confirmed_after_neckline_break(self):
        closes = [100] * 35
        closes[5], closes[10], closes[16], closes[22], closes[27], closes[-1] = 110, 95, 125, 95, 109, 91
        self.assert_pattern(closes, "Head and Shoulders", "Bearish", confidence="confirmed")

    def test_cup_and_handle_is_at_most_tentative(self):
        closes = [100, 98, 95, 91, 87, 84, 81, 79, 78, 78, 79, 81, 84, 88, 92, 96, 99, 100, 99, 98, 97, 98, 99, 99, 100, 100, 100, 100, 100, 100]
        results = detect_chart_patterns(make_rows(closes), lookback_days=90)
        matches = [item for item in results if item["pattern_name"] == "Cup and Handle"]
        self.assertTrue(matches)
        self.assertIn(matches[0]["confidence_level"], ("tentative", "confirmed"))

    def test_inverted_cup_and_handle_is_at_most_tentative(self):
        closes = [100, 102, 105, 109, 113, 116, 119, 121, 122, 122, 121, 119, 116, 112, 108, 104, 101, 100, 101, 102, 103, 102, 101, 101, 100, 100, 100, 100, 100, 100]
        results = detect_chart_patterns(make_rows(closes), lookback_days=90)
        matches = [item for item in results if item["pattern_name"] == "Inverted Cup and Handle"]
        self.assertTrue(matches)
        self.assertIn(matches[0]["confidence_level"], ("tentative", "confirmed"))

    def test_flat_data_has_no_patterns(self):
        self.assertEqual(detect_chart_patterns(make_rows([100] * 90)), [])
