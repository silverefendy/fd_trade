from fd_trade.fd_trade.tests.base import FDTradeTestCase
from fd_trade.utils.price_data import calculate_market_regime


class TestIHSGSignal(FDTradeTestCase):
    def test_all_market_regimes(self):
        self.assertEqual(calculate_market_regime("Bullish Kuat", 110, 100, 105), "Risk-On")
        self.assertEqual(calculate_market_regime("Bullish Lemah", 110, 100, 105), "Risk-On")
        self.assertEqual(calculate_market_regime("Sideways"), "Neutral")
        self.assertEqual(calculate_market_regime("Bearish Lemah"), "Risk-Off")
        self.assertEqual(calculate_market_regime("Bearish Kuat"), "Avoid New Entry")
