import tempfile
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from fd_trade.fd_trade.tests.base import FDTradeTestCase
from fd_trade.fd_trade.doctype.broker_summary.broker_summary import parse_excel_value


class TestBrokerSummary(FDTradeTestCase):
    def test_parse_excel_values_and_thresholds(self):
        self.assertEqual(parse_excel_value("15M"), 15_000_000)
        self.assertEqual(parse_excel_value("-15"), -15.0)
        self.assertIsNone(parse_excel_value("invalid"))

    def test_insight_thresholds(self):
        from fd_trade.fd_trade.doctype.broker_summary.broker_summary import BrokerSummary
        doc = BrokerSummary({"doctype": "Broker Summary", "avg_pct": 15, "price": 100, "average_price": 110})
        doc.generate_insight_notes()
        self.assertIn("BIG ACCUMULATION", doc.insight_notes)

    def test_import_from_excel_uses_dummy_workbook(self):
        from fd_trade.fd_trade.doctype.broker_summary import broker_summary
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "broker.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet["B7"] = "2026-09-19"
            sheet["B9"] = "1M"; sheet["C9"] = "20"
            sheet["B10"] = "2M"; sheet["C10"] = "25"
            sheet["B11"] = "3M"; sheet["C11"] = "30"
            sheet["B12"] = "4M"; sheet["C12"] = "16"
            sheet["B15"] = 1; sheet["C15"] = 1
            sheet["B16"] = "1M"; sheet["B17"] = "2M"; sheet["B18"] = 6500
            sheet["A20"] = "YP"; sheet["B20"] = "1M"; sheet["C20"] = 10
            sheet["F20"] = "CC"; sheet["G20"] = "500K"; sheet["H20"] = 5
            workbook.save(filename)
            doc = MagicDoc()
            with patch.object(broker_summary.frappe, "get_doc", return_value=doc), \
                    patch.object(broker_summary.frappe, "get_site_path", return_value=str(filename)), \
                    patch.object(broker_summary.frappe.utils, "get_url_path", return_value="/broker.xlsx"), \
                    patch.object(broker_summary.frappe, "msgprint"):
                result = broker_summary.import_from_excel("BROKER-TEST", "/broker.xlsx", "BBCA")
            self.assertTrue(result["success"])
            self.assertEqual(result["imported"], 2)


class MagicDoc:
    def __init__(self):
        self.broker_details = []

    def append(self, fieldname, value):
        getattr(self, fieldname).append(value)

    def save(self):
        return None
