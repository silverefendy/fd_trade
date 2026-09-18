from fd_trade.fd_trade.tests.base import FDTradeTestCase
from fd_trade.utils.risk_engine import calculate_position_sizing, get_open_exposure


class TestRiskEngine(FDTradeTestCase):
    def test_position_sizing_respects_all_limits(self):
        import frappe
        settings = frappe.get_single("Trading Account Settings")
        result = calculate_position_sizing("BBCA", 6500, 100, settings=settings)
        self.assertIsNotNone(result)
        self.assertEqual(result["final_lot"], min(result["lot_by_risk"], result["lot_by_max_per_stock"], result["lot_by_max_exposure"]))
        self.assertIn(result["limiting_factor"], {"risk", "max_per_stock", "max_exposure"})

    def test_open_exposure_returns_tuple(self):
        per_stock, total = get_open_exposure("BBCA")
        self.assertGreaterEqual(per_stock, 0)
        self.assertGreaterEqual(total, 0)
