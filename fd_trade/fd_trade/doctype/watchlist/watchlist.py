"""
Watchlist Controller
Manages stock watchlist with tier classification.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now


class Watchlist(Document):
    """Watchlist entry for tracking potential trading opportunities."""

    def before_save(self):
        """Update last_updated timestamp before saving."""
        self.last_updated = now()


@frappe.whitelist()
def fetch_support_resistance(docname):
    """Ambil & simpan level Support/Resistance untuk Watchlist tertentu."""
    from fd_trade.utils.price_data import get_support_resistance

    doc = frappe.get_doc("Watchlist", docname)
    result = get_support_resistance(doc.ticker)

    if not result:
        frappe.throw(_("Gagal mengambil data Support/Resistance untuk ticker {0}. Cek nama ticker atau koneksi.").format(doc.ticker))

    doc.support_level = result["support_level"]
    doc.resistance_level = result["resistance_level"]
    doc.sr_details = result["details"]
    doc.save()

    return result
