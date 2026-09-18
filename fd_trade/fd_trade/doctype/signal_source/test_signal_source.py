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

    def test_insert_without_ticker_is_rejected(self):
        source_type = self.select_options("Signal Source", "source_type")[0]
        doc = frappe.get_doc({
            "doctype": "Signal Source",
            "source_type": source_type,
            "source_name": "Test",
            "ticker": "",
            "date_received": frappe.utils.today(),
            "status": "New",
        })
        with self.assertRaises(frappe.MandatoryError):
            doc.insert(ignore_permissions=True)
