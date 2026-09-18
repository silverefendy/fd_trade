from fd_trade.fd_trade.tests.base import FDTradeTestCase
import frappe


class TestTradingAccountSettings(FDTradeTestCase):
    def test_single_settings_can_save_defaults(self):
        settings = frappe.get_single("Trading Account Settings")
        settings.modal_total = 30_000_000
        settings.risk_per_trade_percent = 0.5
        settings.save(ignore_permissions=True)
        self.assertEqual(settings.modal_total, 30_000_000)

    def test_password_is_stored_through_frappe_password_api(self):
        settings = frappe.get_single("Trading Account Settings")
        settings.telegram_bot_token = "test-token"
        settings.save(ignore_permissions=True)
        self.assertEqual(settings.get_password("telegram_bot_token"), "test-token")
