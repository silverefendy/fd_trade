from unittest.mock import patch

import frappe

from fd_trade.fd_trade.tests.base import FDTradeTestCase
from fd_trade import tasks


class TestTasks(FDTradeTestCase):
    def test_scheduled_jobs_are_fail_silent_on_dependency_error(self):
        functions = [
            tasks.check_intraday_conditions,
            tasks.check_price_alerts,
            tasks.daily_review_notification,
            tasks.weekly_review_notification,
            tasks.monthly_circuit_breaker_check,
            tasks.refresh_all_watchlist,
            tasks.refresh_open_trades_sr,
            tasks.refresh_ihsg_trend,
            tasks.cleanup_old_watchlist_signals,
            tasks.cleanup_old_ihsg_signals,
        ]
        with patch("fd_trade.tasks.frappe.get_single", side_effect=RuntimeError("simulated failure")), \
                patch("fd_trade.tasks.frappe.log_error"):
            for function in functions:
                function()

    @patch("fd_trade.tasks.send_telegram_notification")
    @patch("fd_trade.tasks.frappe.get_all", return_value=[])
    def test_price_alerts_with_no_active_alerts(self, get_all, telegram):
        tasks.check_price_alerts()
        telegram.assert_not_called()

    @patch("fd_trade.tasks.send_telegram_notification")
    def test_review_jobs_do_not_notify_when_limits_are_not_breached(self, telegram):
        # Terisolasi dari data DB nyata: posisi Open sungguhan bisa melewati batas eksposur dan
        # membuat tes ini gagal secara sah. Settings & query bisnis dimock (get_single ikut dimock,
        # jadi frappe.db.sql aman dimock global).
        settings = frappe._dict(
            modal_total=1_000_000, weekly_loss_limit_percent=3, max_exposure_percent=60,
            monthly_circuit_breaker_percent=5, daily_loss_limit_percent=1,
        )
        with patch.object(frappe, "get_single", return_value=settings), \
                patch.object(frappe.db, "sql", return_value=[]):
            tasks.check_intraday_conditions()
            tasks.monthly_circuit_breaker_check()
        telegram.assert_not_called()

    @patch("fd_trade.tasks.send_telegram_notification")
    def test_intraday_alert_is_sent_once_per_day(self, telegram):
        store = {}

        class FakeCache:
            def get_value(self, key):
                return store.get(key)

            def set_value(self, key, value, expires_in_sec=None):
                store[key] = value

        settings = frappe._dict(modal_total=1000, weekly_loss_limit_percent=3, max_exposure_percent=10)

        real_sql = frappe.db.sql

        def fake_sql(query, *args, **kwargs):
            # Hanya intercept 2 query bisnis milik check_intraday_conditions(); query lain
            # (mis. resolusi doctype module / System Settings, dipicu today()->timezone)
            # diteruskan ke frappe.db.sql ASLI -- mock global sebelumnya ikut membajak
            # query framework internal dan merusak cache "doctype_modules".
            if "result_rp" in query:
                return [frappe._dict(total_pnl=0)]
            if "tabTrade Journal" in query:
                return [frappe._dict(total_value=500)]
            return real_sql(query, *args, **kwargs)

        with patch("fd_trade.tasks._cache", return_value=FakeCache()), \
                patch.object(frappe, "get_single", return_value=settings), \
                patch.object(frappe.db, "sql", side_effect=fake_sql):
            tasks.check_intraday_conditions()
            tasks.check_intraday_conditions()
        self.assertEqual(telegram.call_count, 1)
