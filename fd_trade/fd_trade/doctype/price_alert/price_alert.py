"""
Price Alert Controller
Alert untuk harga tertentu (TP/SL/Buy Trigger) yang selalu terikat ke Trade Journal,
baik untuk posisi yang sudah open maupun rencana yang belum entry.
"""

import frappe
from frappe.model.document import Document


class PriceAlert(Document):
    """Price Alert entry - dicek berkala oleh scheduled job check_price_alerts()."""

    def validate(self):
        """Pastikan ticker terisi dari linked_trade jika kosong, dan
        set default condition berdasarkan alert_type jika belum diisi."""
        if not self.ticker and self.linked_trade:
            self.ticker = frappe.db.get_value("Trade Journal", self.linked_trade, "ticker")

        if not self.condition:
            if self.alert_type in ("Take Profit", "Buy Trigger"):
                self.condition = ">="
            elif self.alert_type == "Stop Loss":
                self.condition = "<="
