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
        self.assert_pattern([100, 90, 110, 92, 108, 105, 104], "Double Bottom", "Bullish")

    def test_double_top(self):
        self.assert_pattern([100, 110, 90, 108, 92, 95, 96], "Double Top", "Bearish")

    def test_inverse_head_and_shoulders(self):
        self.assert_pattern([100, 90, 100, 75, 100, 91, 100, 102], "Inverse Head and Shoulders", "Bullish")

    def test_head_and_shoulders(self):
        self.assert_pattern([100, 110, 100, 125, 100, 109, 100, 98], "Head and Shoulders", "Bearish")

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

