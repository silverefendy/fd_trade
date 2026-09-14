"""
Trade Journal Controller
Core logging doctype for trading entries with risk management validation.
"""

import frappe
from frappe.model.document import Document
from frappe import _


class TradeJournal(Document):
"""Trade Journal entry with risk management and psychology tracking."""

def validate(self):
"""Validate trade entry and calculate risk metrics."""
self.calculate_risk_metrics()

if self.is_new():
self.check_risk_management_rules()

def calculate_risk_metrics(self):
"""Calculate risk amount, suggested lot, and validate stop loss."""
settings = frappe.get_single("Trading Account Settings")

# Calculate risk per share
risk_per_share = self.entry_price - self.stop_loss

if risk_per_share <= 0:
frappe.throw(_("Stop loss must be below entry price for long positions."))

# Calculate risk amount in rupiah
risk_rp = settings.modal_total * (settings.risk_per_trade_percent / 100)
self.risk_amount = risk_rp

# Calculate suggested lot (rounded down to nearest 100 shares)
suggested_shares = int(risk_rp / risk_per_share)
self.suggested_lot = int(suggested_shares / 100)

# Warn if actual position exceeds suggested risk
if self.position_lot:
actual_risk = self.position_lot * 100 * risk_per_share
if actual_risk > risk_rp * 1.2:  # 20% tolerance
frappe.msgprint(
_("Warning: Actual risk ({0}) exceeds suggested risk ({1}) by more than 20%.").format(
frappe.format_value(actual_risk, {"fieldtype": "Currency"}),
frappe.format_value(risk_rp, {"fieldtype": "Currency"})
)
)

# Calculate result_rp if exit_price is set
if self.exit_price and self.position_lot:
self.result_rp = (self.exit_price - self.entry_price) * self.position_lot * 100

def check_risk_management_rules(self):
"""Check all risk management guard rails before allowing new trade."""
settings = frappe.get_single("Trading Account Settings")

self.check_daily_loss_limit(settings)
self.check_consecutive_losses(settings)
self.check_per_stock_exposure(settings)
self.check_total_exposure(settings)

def check_daily_loss_limit(self, settings):
"""Block new trade if daily loss limit is breached."""
today = frappe.utils.today()
daily_loss_limit = settings.modal_total * (settings.daily_loss_limit_percent / 100)

todays_losses = frappe.db.get_list(
"Trade Journal",
filters={
"date": today,
"status": "Closed",
"result_rp": ["<", 0]
},
fields=["SUM(result_rp) as total_loss"]
)

if todays_losses and todays_losses[0].total_loss:
if todays_losses[0].total_loss <= -daily_loss_limit:
frappe.throw(
_("Daily loss limit breached. Total loss today: {0}. Stop trading per your rules.").format(
frappe.format_value(todays_losses[0].total_loss, {"fieldtype": "Currency"})
)
)

def check_consecutive_losses(self, settings):
"""Block new trade if max consecutive losses reached."""
max_losses = settings.max_consecutive_losses

recent_trades = frappe.db.get_list(
"Trade Journal",
filters={"status": "Closed"},
fields=["result_r"],
order_by="date DESC",
limit=max_losses
)

if len(recent_trades) >= max_losses:
all_losses = all(trade.result_r < 0 for trade in recent_trades if trade.result_r is not None)
if all_losses:
frappe.throw(
_("{0} consecutive losses detected. Stop trading today per your rules.").format(max_losses)
)

def check_per_stock_exposure(self, settings):
"""Block new trade if per-stock exposure limit is exceeded."""
max_per_stock = settings.modal_total * (settings.max_per_stock_percent / 100)

# Get current open positions for this ticker
current_exposure = frappe.db.get_list(
"Trade Journal",
filters={
"ticker": self.ticker,
"status": "Open"
},
fields=["SUM(entry_price * position_lot * 100) as total_value"]
)

current_value = current_exposure[0].total_value if current_exposure and current_exposure[0].total_value else 0
new_position_value = self.entry_price * self.position_lot * 100 if self.position_lot else 0
total_after_new = current_value + new_position_value

if total_after_new > max_per_stock:
frappe.throw(
_("Per-stock exposure limit exceeded. Current: {0}, New: {1}, Limit: {2}").format(
frappe.format_value(current_value, {"fieldtype": "Currency"}),
frappe.format_value(new_position_value, {"fieldtype": "Currency"}),
frappe.format_value(max_per_stock, {"fieldtype": "Currency"})
)
)

def check_total_exposure(self, settings):
"""Block new trade if total portfolio exposure limit is exceeded."""
max_exposure = settings.modal_total * (settings.max_exposure_percent / 100)

# Get all open positions
total_exposure = frappe.db.get_list(
"Trade Journal",
filters={"status": "Open"},
fields=["SUM(entry_price * position_lot * 100) as total_value"]
)

current_total = total_exposure[0].total_value if total_exposure and total_exposure[0].total_value else 0
new_position_value = self.entry_price * self.position_lot * 100 if self.position_lot else 0
total_after_new = current_total + new_position_value

if total_after_new > max_exposure:
frappe.throw(
_("Total portfolio exposure limit exceeded. Current: {0}, New: {1}, Limit: {2}").format(
frappe.format_value(current_total, {"fieldtype": "Currency"}),
frappe.format_value(new_position_value, {"fieldtype": "Currency"}),
frappe.format_value(max_exposure, {"fieldtype": "Currency"})
)
)

def on_update(self):
"""Trigger Telegram notification when trade is closed."""
if self.status == "Closed" and self.exit_price and self.result_r is not None:
self.notify_on_close()


def notify_on_close(doc, method=None):
"""Send Telegram notification when a trade is closed."""
from fd_trade.utils.telegram import send_telegram_notification

followed_status = "Yes" if doc.followed_system else "No"
message = "Trade Closed\\nTicker: " + doc.ticker + "\\nResult R: " + str(doc.result_r) + "R\\nFollowed System: " + followed_status

send_telegram_notification(message)
