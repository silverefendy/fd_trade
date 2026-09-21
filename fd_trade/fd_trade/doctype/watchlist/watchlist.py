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

    def before_insert(self):
        """Uppercase ticker SEBELUM proses naming (autoname: field:ticker) berjalan.
        Ini WAJIB di before_insert(), bukan validate()/before_save(), karena
        Frappe memanggil set_new_name() sebelum run_before_save_methods()
        di pipeline Document.insert() -- lihat frappe/model/document.py.
        """
        if self.ticker:
            self.ticker = self.ticker.strip().upper()

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
        self._pending_sr_history = None
        if sr_result:
            self.support_level = sr_result["support_level"]
            self.support_level_2 = sr_result["support_level_2"]
            self.support_level_3 = sr_result["support_level_3"]
            self.resistance_level = sr_result["resistance_level"]
            self.resistance_level_2 = sr_result["resistance_level_2"]
            self.resistance_level_3 = sr_result["resistance_level_3"]
            self.sr_details = sr_result["details"]
            self.trend_status = sr_result.get("trend")
            # BUG #10 FIX (19 Sep 2026): simpan history mentah untuk dipakai
            # ulang oleh create_signal() di on_update(), hindari fetch dobel.
            self._pending_sr_history = sr_result.get("price_history_rows")

            # BUG FIX (19 Sep 2026): volume_status tidak pernah diisi untuk
            # Watchlist -- sebelumnya get_volume_confirmation() hanya
            # dipanggil dari create_signal() (watchlist_signal.py). Reuse
            # history dari get_support_resistance() supaya tidak fetch dobel.
            # Import lokal (bukan ubah baris import atas yang dipakai 3
            # fungsi berbeda di file ini, utk hindari ambiguitas match).
            from fd_trade.utils.price_data import get_volume_confirmation
            vol_result = get_volume_confirmation(self.ticker, price_history_rows=sr_result.get("price_history_rows"))
            if vol_result:
                self.avg_volume_20d = vol_result.get("avg_volume_20d") or 0
                self.volume_status = vol_result.get("volume_status")

        # BUG FIX (18 Sep 2026): create_signal() TIDAK boleh dipanggil di sini
        # (before_save). Untuk dokumen BARU, self.name sudah ter-set (autoname
        # field:ticker) tapi baris belum ter-INSERT ke DB -- create_signal()
        # insert Watchlist Signal dengan Link field "watchlist" akan gagal
        # validasi Link (baris Watchlist belum ada), fail-silent, log:
        # "Could not find Watchlist: <ticker>". Signal pertama pada watchlist
        # baru SELALU gagal dibuat diam-diam. Fix: tunda ke on_update()
        # (jalan setelah INSERT/UPDATE selesai) via flag ini.
        self._pending_signal_refresh = True

    def on_update(self):
        """Buat Watchlist Signal SETELAH dokumen ini benar-benar ter-insert/
        ter-update di DB (bukan di before_save()), supaya field Link
        'watchlist' di Watchlist Signal tidak gagal validasi -- lihat
        catatan BUG FIX di _auto_fetch_price_data()."""
        if getattr(self, "_pending_signal_refresh", False):
            self._pending_signal_refresh = False
            from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import create_signal
            create_signal(
                watchlist_name=self.name,
                ticker=self.ticker,
                current_price=self.current_price,
                trend_status=self.trend_status,
                support_level=self.support_level,
                support_level_2=self.support_level_2,
                resistance_level=self.resistance_level,
                support_level_3=self.support_level_3,
                resistance_level_2=self.resistance_level_2,
                resistance_level_3=self.resistance_level_3,
                history=getattr(self, "_pending_sr_history", None),
            )


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
    doc.support_level_3 = result["support_level_3"]
    doc.resistance_level = result["resistance_level"]
    doc.resistance_level_2 = result["resistance_level_2"]
    doc.resistance_level_3 = result["resistance_level_3"]
    doc.sr_details = result["details"]
    doc.trend_status = result.get("trend")

    # VOLUME FIX (20 Sep 2026): isi volume_status & avg_volume_20d juga saat
    # refresh manual (sebelumnya kosong utk record lama).
    from fd_trade.utils.price_data import get_volume_confirmation
    vol_result = get_volume_confirmation(doc.ticker, price_history_rows=result.get("price_history_rows"))
    if vol_result:
        doc.avg_volume_20d = vol_result.get("avg_volume_20d") or 0
        doc.volume_status = vol_result.get("volume_status")
    doc.save()

    from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import create_signal
    create_signal(
        watchlist_name=doc.name,
        ticker=doc.ticker,
        current_price=doc.current_price,
        trend_status=doc.trend_status,
        support_level=doc.support_level,
        support_level_2=doc.support_level_2,
        resistance_level=doc.resistance_level,
        support_level_3=doc.support_level_3,
        resistance_level_2=doc.resistance_level_2,
        resistance_level_3=doc.resistance_level_3,
        history=result.get("price_history_rows"),
    )

    return result


@frappe.whitelist()
def refresh_current_price(docname):
    """Ambil & simpan current price + OHLC terbaru untuk Watchlist tertentu
    (dipanggil manual dari tombol UI "Refresh Harga Sekarang").
    Tidak menyentuh Support/Resistance -- itu tugas fetch_support_resistance()."""
    from fd_trade.utils.price_data import get_current_price, get_current_ohlc

    doc = frappe.get_doc("Watchlist", docname)
    price = get_current_price(doc.ticker)

    if price is None:
        frappe.throw(
            _("Gagal mengambil harga terkini untuk ticker {0}. Cek nama ticker atau koneksi.").format(doc.ticker)
        )

    doc.current_price = price

    ohlc = get_current_ohlc(doc.ticker)
    if ohlc:
        doc.open_price = ohlc["open"]
        doc.high_price = ohlc["high"]
        doc.low_price = ohlc["low"]
        doc.close_price = ohlc["close"]

    doc.last_updated = now()
    doc.save()

    from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import create_signal
    create_signal(
        watchlist_name=doc.name,
        ticker=doc.ticker,
        current_price=doc.current_price,
        trend_status=doc.trend_status,
        support_level=doc.support_level,
        support_level_2=doc.support_level_2,
        resistance_level=doc.resistance_level,
        support_level_3=doc.support_level_3,
        resistance_level_2=doc.resistance_level_2,
        resistance_level_3=doc.resistance_level_3,
    )

    return {"current_price": doc.current_price}
