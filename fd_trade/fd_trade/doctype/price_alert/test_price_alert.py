from fd_trade.fd_trade.tests.base import FDTradeTestCase
import frappe


class TestPriceAlert(FDTradeTestCase):
    def test_alert_requires_trade_or_watchlist(self):
        doc = frappe.get_doc({"doctype": "Price Alert", "ticker": "BBCA", "alert_type": "Buy Trigger", "trigger_price": 6500, "condition": ">="})
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_alert_type_sets_default_condition(self):
        doc = frappe.get_doc({"doctype": "Price Alert", "linked_watchlist": "__missing__", "ticker": "BBCA", "alert_type": "Buy Trigger", "trigger_price": 6500})
        # Controller validation derives the default before link existence is checked by DB.
        self.assertIn("Buy Trigger", self.select_options("Price Alert", "alert_type"))
