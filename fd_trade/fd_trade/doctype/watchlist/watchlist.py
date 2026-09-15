"""
Watchlist Controller
Manages stock watchlist with tier classification.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class Watchlist(Document):
    """Watchlist entry for tracking potential trading opportunities."""

    def before_save(self):
        """Update timestamp, dan auto-fetch current price + S/R setiap kali
        record baru dibuat atau ticker berubah dari sebelumnya."""
        if self.ticker:
            self.ticker = self.ticker.strip().upper()
        self.last_updated = now()

        ticker_changed = self.is_new() or self.has_value_changed("ticker")

        if ticker_changed and self.ticker:
            self._auto_fetch_price_data()

    def _auto_fetch_price_data(self):
        """Ambil current price & Support/Resistance otomatis, fail-silent
        (tidak menghentikan proses save kalau yfinance gagal/timeout)."""
        from fd_trade.utils.price_data import get_current_price, get_current_ohlc, get_support_resistance

        price = get_current_price(self.ticker)
        if price is not None:
            self.current_price = price

        ohlc = get_current_ohlc(self.ticker)
        if ohlc:
            self.open_price = ohlc["open"]
            self.high_price = ohlc["high"]
            self.low_price = ohlc["low"]
            self.close_price = ohlc["close"]

        sr_result = get_support_resistance(self.ticker)
        if sr_result:
            self.support_level = sr_result["support_level"]
            self.support_level_2 = sr_result["support_level_2"]
            self.resistance_level = sr_result["resistance_level"]
            self.resistance_level_2 = sr_result["resistance_level_2"]
            self.sr_details = sr_result["details"]


@frappe.whitelist()
def fetch_support_resistance(docname):
    """Ambil & simpan level Support/Resistance untuk Watchlist tertentu
    (dipanggil manual dari tombol UI untuk refresh data)."""
    from fd_trade.utils.price_data import get_current_price, get_current_ohlc, get_support_resistance

    doc = frappe.get_doc("Watchlist", docname)
    result = get_support_resistance(doc.ticker)

    if not result:
        frappe.throw(
            _("Gagal mengambil data Support/Resistance untuk ticker {0}. Cek nama ticker atau koneksi.").format(doc.ticker)
        )

    price = get_current_price(doc.ticker)
    if price is not None:
        doc.current_price = price

    ohlc = get_current_ohlc(doc.ticker)
    if ohlc:
        doc.open_price = ohlc["open"]
        doc.high_price = ohlc["high"]
        doc.low_price = ohlc["low"]
        doc.close_price = ohlc["close"]

    doc.support_level = result["support_level"]
    doc.support_level_2 = result["support_level_2"]
    doc.resistance_level = result["resistance_level"]
    doc.resistance_level_2 = result["resistance_level_2"]
    doc.sr_details = result["details"]
    doc.save()

    return result
