from unittest.mock import MagicMock, patch

from fd_trade.fd_trade.tests.base import FDTradeTestCase
from fd_trade.utils.telegram import send_telegram_notification


class TestTelegram(FDTradeTestCase):
    @patch("fd_trade.utils.telegram.requests.post")
    def test_notification_uses_mocked_http_only(self, post):
        post.return_value = MagicMock(raise_for_status=MagicMock())
        import frappe
        settings = frappe.get_single("Trading Account Settings")
        settings.telegram_notifications_enabled = 1
        settings.telegram_chat_id = "chat"
        settings.telegram_bot_token = "token"
        settings.save(ignore_permissions=True)
        send_telegram_notification("test FD-Trade")
        # Frappe password encryption may prevent a local token from being read in some setups.
        # The assertion remains on the mocked boundary: never call Telegram outside this mock.
        post.assert_called_once()
