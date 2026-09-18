from unittest.mock import patch

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
    @patch("fd_trade.tasks.frappe.db.sql", return_value=[{"total_pnl": 0}])
    def test_review_jobs_do_not_notify_when_limits_are_not_breached(self, sql, telegram):
        tasks.check_intraday_conditions()
        tasks.monthly_circuit_breaker_check()
        telegram.assert_not_called()
