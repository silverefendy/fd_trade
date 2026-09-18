from unittest.mock import MagicMock, patch

from fd_trade.fd_trade.tests.base import FDTradeTestCase
from fd_trade.fd_trade.doctype.trade_journal.trade_journal import TradeJournal


class TestTradeJournal(FDTradeTestCase):
    def test_select_options_are_loaded_from_json(self):
        self.assertIn("Moderate (2.5R)", self.select_options("Trade Journal", "target_category"))

    def test_target_price_three_r_multiples(self):
        doc = TradeJournal({"doctype": "Trade Journal", "entry_price": 1000, "stop_loss": 900})
        doc.target_category = "Moderate (2.5R)"
        doc.calculate_target_price(100)
        self.assertIn("Conservative (1.5R): Rp1,150", doc.target_suggestions)
        self.assertIn("Moderate (2.5R): Rp1,250", doc.target_suggestions)
        self.assertIn("Aggressive (4R): Rp1,400", doc.target_suggestions)

    def test_risk_rule_methods_block_when_limits_are_exceeded(self):
        settings = MagicMock(modal_total=30_000_000, daily_loss_limit_percent=1, max_consecutive_losses=3, max_per_stock_percent=15, max_exposure_percent=60)
        doc = TradeJournal({"doctype": "Trade Journal", "ticker": "BBCA", "entry_price": 6500, "position_lot": 100})
        with patch("frappe.db.sql", return_value=[{"total_loss": -300_000}]), self.assertRaises(Exception):
            doc.check_daily_loss_limit(settings)
        with patch("frappe.db.get_list", return_value=[{"result_r": -1}, {"result_r": -1}, {"result_r": -1}]), self.assertRaises(Exception):
            doc.check_consecutive_losses(settings)
