from fd_trade.fd_trade.tests.base import FDTradeTestCase
import frappe


class TestSignalSource(FDTradeTestCase):
    def test_select_options_are_loaded_from_doctype_json(self):
        options = self.select_options("Signal Source", "status")
        self.assertTrue(options)

    def test_reliability_without_closed_trades(self):
        from fd_trade.fd_trade.doctype.signal_source.signal_source import calculate_reliability_score
        result = calculate_reliability_score("__missing_source__")
        self.assertEqual(result["sample_size"], 0)

    def test_promote_requires_ticker(self):
        from fd_trade.fd_trade.doctype.signal_source.signal_source import promote_to_watchlist
        doc = frappe.get_doc({"doctype": "Signal Source", "source_name": "Test", "status": "New"})
        doc.insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            promote_to_watchlist(doc.name)
