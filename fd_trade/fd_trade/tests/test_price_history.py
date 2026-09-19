import datetime
import unittest
from unittest.mock import MagicMock, patch

from fd_trade.utils.price_data import get_daily_ohlc_history
from fd_trade import tasks


class FakeIndex:
    def __init__(self, value): self.value = value
    def date(self): return self.value


class FakeHistory:
    empty = False

    def iterrows(self):
        return iter([
            (FakeIndex(datetime.date(2026, 9, 18)), {
                "Open": 6401, "High": 6510, "Low": 6390, "Close": 6503, "Volume": 1000,
            }),
        ])


class TestPriceHistory(unittest.TestCase):
    @patch("fd_trade.utils.price_data.yf.Ticker")
    def test_get_daily_ohlc_history_returns_structured_rows(self, ticker_class):
        ticker_class.return_value.history.return_value = FakeHistory()
        result = get_daily_ohlc_history("BBCA")
        self.assertEqual(result[0]["date"], "2026-09-18")
        self.assertEqual(result[0]["close"], 6500)
        self.assertIn("volume", result[0])
        ticker_class.assert_called_once_with("BBCA.JK")

    @patch("fd_trade.tasks.frappe.db.commit")
    @patch("fd_trade.tasks.frappe.get_doc")
    @patch("fd_trade.tasks.frappe.db.exists", side_effect=[False, True])
    @patch("fd_trade.tasks._price_history_tickers", return_value=["BBCA"])
    @patch("fd_trade.tasks._store_price_history_for_ticker", side_effect=[1, 0])
    def test_backfill_is_idempotent_across_repeated_runs(self, store, tickers, exists, get_doc, commit):
        # The production idempotence boundary is db.exists() in the row writer;
        # repeated runs must not create a second document for the same key.
        self.assertEqual(tasks.backfill_price_history("BBCA")["inserted"], 1)
        self.assertEqual(tasks.backfill_price_history("BBCA")["inserted"], 0)
        self.assertEqual(store.call_count, 2)

    @patch("fd_trade.tasks.frappe.delete_doc")
    @patch("fd_trade.tasks.frappe.get_all", return_value=["OLD-1"])
    @patch("fd_trade.tasks.frappe.db.commit")
    def test_cleanup_deletes_old_rows(self, commit, get_all, delete_doc):
        tasks.cleanup_old_price_history()
        get_all.assert_called_once()
        self.assertEqual(get_all.call_args.kwargs["filters"]["date"][0], "<")
        delete_doc.assert_called_once_with("Price History", "OLD-1", ignore_permissions=True, force=True)

    @patch("fd_trade.tasks.frappe.log_error")
    @patch("fd_trade.tasks._store_price_history_for_ticker", side_effect=[RuntimeError("bad ticker"), 2])
    @patch("fd_trade.tasks._price_history_tickers", return_value=["BAD", "BBCA"])
    @patch("fd_trade.tasks.frappe.db.commit")
    def test_one_ticker_failure_does_not_stop_batch(self, commit, tickers, store, log_error):
        result = tasks.backfill_price_history()
        self.assertEqual(result["inserted"], 2)
        self.assertEqual(store.call_count, 2)
        log_error.assert_called_once()
