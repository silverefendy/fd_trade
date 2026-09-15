"""
Price Alert Controller
Alert untuk harga tertentu (TP/SL/Buy Trigger), bisa terikat ke Trade Journal
(posisi open/rencana entry) ATAU ke Watchlist (kandidat yang belum entry).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class PriceAlert(Document):
    """Price Alert entry - dicek berkala oleh scheduled job check_price_alerts()."""

    def validate(self):
        """Pastikan minimal satu sumber (Trade Journal atau Watchlist) terisi,
        ticker otomatis fetch dari sumber yang terisi, dan default condition
        berdasarkan alert_type jika belum diisi."""

        if not self.linked_trade and not self.linked_watchlist:
            frappe.throw(_("Price Alert harus terhubung ke Trade Journal atau Watchlist."))

        if not self.ticker:
            if self.linked_trade:
                self.ticker = frappe.db.get_value("Trade Journal", self.linked_trade, "ticker")
            elif self.linked_watchlist:
                self.ticker = frappe.db.get_value("Watchlist", self.linked_watchlist, "ticker")

        if not self.condition:
            if self.alert_type in ("Take Profit", "Buy Trigger"):
                self.condition = ">="
            elif self.alert_type == "Stop Loss":
                self.condition = "<="
