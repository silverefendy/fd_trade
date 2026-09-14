"""
Telegram Utility Module
Handles Telegram Bot API notifications for the trading system.
"""

import requests
import frappe


def send_telegram_notification(message):
"""Send a message via Telegram Bot API using credentials stored in Trading Account Settings.

Fails silently with a logged error if telegram_notifications_enabled is off or credentials 
are missing -- must never crash the calling process.

Args:
message (str): The message to send via Telegram
"""
try:
settings = frappe.get_single("Trading Account Settings")
except frappe.DoesNotExistError:
frappe.log_error("Trading Account Settings not found", "FD-Trade Telegram")
return

if not settings.telegram_notifications_enabled:
return

if not settings.telegram_bot_token or not settings.telegram_chat_id:
frappe.log_error("Telegram credentials missing", "FD-Trade Telegram")
return

url = f"https://api.telegram.org/bot{settings.get_password('telegram_bot_token')}/sendMessage"
payload = {
"chat_id": settings.telegram_chat_id,
"text": message,
"parse_mode": "Markdown"
}

try:
response = requests.post(url, data=payload, timeout=10)
response.raise_for_status()
except Exception as e:
frappe.log_error(f"Telegram send failed: {e}", "FD-Trade Telegram")
