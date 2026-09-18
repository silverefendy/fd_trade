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


def _build_recommendation_change_message(ticker, previous_recommendation,
                                          recommendation, current_price,
                                          recommendation_price_low=None,
                                          recommendation_price_high=None,
                                          stop_loss=None, notes=None):
    """Buat pesan Telegram hanya jika recommendation berubah."""
    if not previous_recommendation or previous_recommendation == recommendation:
        return None
    price_text = f"Rp{current_price:,.0f}" if current_price is not None else "harga tidak tersedia"
    message = f"Sinyal berubah: {ticker} {previous_recommendation} -> {recommendation} @ {price_text}"
    if recommendation == "Buy":
        zone = f"Rp{recommendation_price_low:,.0f} - Rp{recommendation_price_high:,.0f}" \
            if recommendation_price_low is not None and recommendation_price_high is not None \
            else "tidak tersedia"
        stop_loss_text = f"Rp{stop_loss:,.0f}" if stop_loss is not None else "tidak tersedia"
        message += f" | Entry zone: {zone} | Stop loss: {stop_loss_text}"
    elif recommendation in ("Avoid", "Sell") and notes:
        message += f" | Alasan: {notes}"
    return message


def create_signal(watchlist_name, ticker, current_price, trend_status,
                   support_level, support_level_2, resistance_level,
                   support_level_3=None, resistance_level_2=None,
                   resistance_level_3=None):
    """Hitung recommendation (Fase 1, rule-based) dan simpan sebagai record
    baru di Watchlist Signal -- dipanggil dari watchlist.py (before_save,
    fetch manual) dan tasks.py (refresh_all_watchlist scheduler).

    Fail-silent: kalau ada error, di-log tapi tidak menghentikan proses
    fetch harga yang sedang berjalan (konsisten dengan filosofi fail-silent
    aplikasi ini untuk hal non-kritikal)."""
    import frappe
    from fd_trade.utils.price_data import calculate_recommendation
    from fd_trade.utils.price_data import get_pivot_points, check_confluence
    from fd_trade.utils.price_data import get_nearest_level, get_volume_confirmation
    from fd_trade.utils.price_data import PROXIMITY_THRESHOLD_PCT, VOLUME_HIGH_RATIO, VOLUME_LOW_RATIO
    from fd_trade.utils.telegram import send_telegram_notification

    try:
        settings = frappe.get_single("Trading Account Settings")
        proximity_threshold = settings.proximity_threshold_pct or PROXIMITY_THRESHOLD_PCT
        volume_high_ratio = settings.volume_high_ratio or VOLUME_HIGH_RATIO
        volume_low_ratio = settings.volume_low_ratio or VOLUME_LOW_RATIO
        ihsg_trend = settings.ihsg_trend
        ihsg_latest = frappe.get_all(
            "IHSG Signal",
            fields=["market_regime", "trend_status", "ihsg_price", "timestamp"],
            order_by="timestamp desc",
            limit=1,
        )

        levels = {
            "support_level": support_level,
            "support_level_2": support_level_2,
            "support_level_3": support_level_3,
            "resistance_level": resistance_level,
            "resistance_level_2": resistance_level_2,
            "resistance_level_3": resistance_level_3,
        }
        proximity = get_nearest_level(current_price, levels, proximity_threshold)
        volume = get_volume_confirmation(
            ticker,
            high_ratio=volume_high_ratio,
            low_ratio=volume_low_ratio,
        )

        confluence_text = "Pivot point tidak tersedia."
        pivot = get_pivot_points(ticker)
        if pivot:
            is_conf_s, delta_s = check_confluence(support_level, pivot["S1"])
            is_conf_r, delta_r = check_confluence(resistance_level, pivot["R1"])
            confluence_text = (
                f"Pivot S1={pivot['S1']} (selisih {delta_s}%, "
                f"{'CONFLUENT' if is_conf_s else 'divergen'}) | "
                f"Pivot R1={pivot['R1']} (selisih {delta_r}%, "
                f"{'CONFLUENT' if is_conf_r else 'divergen'})"
            )

        rec = calculate_recommendation(
            ticker=ticker,
            current_price=current_price,
            trend=trend_status,
            support_level=support_level,
            support_level_2=support_level_2,
            resistance_level=resistance_level,
            support_level_3=support_level_3,
            resistance_level_2=resistance_level_2,
            resistance_level_3=resistance_level_3,
            ihsg_trend=ihsg_trend,
            proximity=proximity,
            volume_status=volume.get("volume_status") if volume else None,
        )

        notes = rec.get("notes")
        if notes:
            confluence_text = f"{confluence_text} | {notes}"

        previous_signal = None
        try:
            previous_signals = frappe.get_all(
                "Watchlist Signal",
                filters={"ticker": ticker},
                fields=["recommendation"],
                order_by="timestamp desc",
                limit=1,
            )
            previous_signal = previous_signals[0] if previous_signals else None
        except Exception as e:
            frappe.log_error(
                f"Gagal membaca signal sebelumnya untuk {ticker}: {e}",
                "FD-Trade Watchlist Signal Notification",
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
            "stop_loss": rec.get("stop_loss"),
            "sizing_limiting_factor": rec.get("sizing_limiting_factor"),
            "confluence_notes": confluence_text,
            "notes": notes,
            "nearest_level_name": proximity.get("level_name") if proximity else None,
            "nearest_level_distance_pct": proximity.get("distance_pct") if proximity else None,
            "proximity_category": proximity.get("category") if proximity else None,
            "volume_status": volume.get("volume_status") if volume else None,
            "current_volume": volume.get("current_volume") if volume else None,
            "avg_volume_20d": volume.get("avg_volume_20d") if volume else None,
            "take_profit_next": rec.get("take_profit_next"),
            "take_profit_extended": rec.get("take_profit_extended"),
            "ihsg_context": (
                f"{ihsg_latest[0].market_regime} ({ihsg_latest[0].trend_status})"
                if ihsg_latest else ihsg_trend
            ),
            "risk_amount": rec.get("risk_amount"),
            "risk_per_share": rec.get("risk_per_share"),
            "suggested_lot": rec.get("suggested_lot"),
            "suggested_position_rp": rec.get("suggested_position_rp"),
        })
        signal.insert(ignore_permissions=True)
        frappe.db.commit()
        if previous_signal:
            try:
                notification = _build_recommendation_change_message(
                    ticker=ticker,
                    previous_recommendation=previous_signal.recommendation,
                    recommendation=rec.get("recommendation"),
                    current_price=current_price,
                    recommendation_price_low=rec.get("recommendation_price_low"),
                    recommendation_price_high=rec.get("recommendation_price_high"),
                    stop_loss=rec.get("stop_loss"),
                    notes=notes,
                )
                if notification:
                    send_telegram_notification(notification)
            except Exception as e:
                frappe.log_error(
                    f"Gagal mengirim perubahan signal untuk {ticker}: {e}",
                    "FD-Trade Watchlist Signal Notification",
                )
        return signal

    except Exception as e:
        frappe.log_error(f"create_signal failed for {ticker}: {e}", "FD-Trade Watchlist Signal")
        return None
