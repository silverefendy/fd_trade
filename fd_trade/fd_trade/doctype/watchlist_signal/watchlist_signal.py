"""
Watchlist Signal Controller
Histori snapshot rekomendasi Buy/Wait/Sell/Avoid per ticker, dibuat setiap
kali fetch data dijalankan (before_save, fetch manual, atau scheduler).
Bersifat log/append-only -- tidak diedit setelah dibuat.
Auto-dibersihkan setelah 60 hari via fd_trade.tasks.cleanup_old_watchlist_signals.
"""

from frappe.model.document import Document


class WatchlistSignal(Document):
    pass


def create_signal(watchlist_name, ticker, current_price, trend_status,
                   support_level, support_level_2, resistance_level):
    """Hitung recommendation (Fase 1, rule-based) dan simpan sebagai record
    baru di Watchlist Signal -- dipanggil dari watchlist.py (before_save,
    fetch manual) dan tasks.py (refresh_all_watchlist scheduler).

    Fail-silent: kalau ada error, di-log tapi tidak menghentikan proses
    fetch harga yang sedang berjalan (konsisten dengan filosofi fail-silent
    aplikasi ini untuk hal non-kritikal)."""
    import frappe
    from fd_trade.utils.price_data import calculate_recommendation

    try:
        rec = calculate_recommendation(
            ticker=ticker,
            current_price=current_price,
            trend=trend_status,
            support_level=support_level,
            support_level_2=support_level_2,
            resistance_level=resistance_level,
        )

        signal = frappe.get_doc({
            "doctype": "Watchlist Signal",
            "watchlist": watchlist_name,
            "ticker": ticker,
            "timestamp": frappe.utils.now(),
            "current_price": current_price,
            "trend_status": trend_status,
            "recommendation": rec.get("recommendation"),
            "recommendation_price_low": rec.get("recommendation_price_low"),
            "recommendation_price_high": rec.get("recommendation_price_high"),
            "risk_amount": rec.get("risk_amount"),
            "risk_per_share": rec.get("risk_per_share"),
            "suggested_lot": rec.get("suggested_lot"),
            "suggested_position_rp": rec.get("suggested_position_rp"),
        })
        signal.insert(ignore_permissions=True)
        frappe.db.commit()
        return signal

    except Exception as e:
        frappe.log_error(f"create_signal failed for {ticker}: {e}", "FD-Trade Watchlist Signal")
        return None
