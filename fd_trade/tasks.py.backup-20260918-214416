"""
Scheduled Tasks Module
Contains functions for scheduled jobs via Frappe scheduler.
"""

import frappe
from frappe.utils import today, getdate, add_to_date, flt
from fd_trade.utils.telegram import send_telegram_notification


def check_intraday_conditions():
    """Check intraday conditions and send warnings if limits are breached.

    Runs every 30 minutes during trading hours (9-16, Mon-Fri).
    """
    try:
        settings = frappe.get_single("Trading Account Settings")

        # Calculate current weekly realized P&L
        monday = get_monday_of_current_week()
        weekly_result = frappe.db.sql(
            """
            SELECT SUM(result_rp) as total_pnl
            FROM `tabTrade Journal`
            WHERE date >= %s AND status = 'Closed'
            """,
            (monday,),
            as_dict=True
        )

        weekly_pnl = weekly_result[0].total_pnl if weekly_result and weekly_result[0].total_pnl else 0
        weekly_loss_limit = settings.modal_total * (settings.weekly_loss_limit_percent / 100)

        if weekly_pnl <= -weekly_loss_limit:
            message = (
                f"Weekly loss limit breached. Current P&L: {weekly_pnl}. "
                f"Recommend 50% size reduction."
            )
            send_telegram_notification(message)

        # Check total open exposure
        exposure_result = frappe.db.sql(
            """
            SELECT SUM(entry_price * position_lot * 100) as total_value
            FROM `tabTrade Journal`
            WHERE status = 'Open'
            """,
            as_dict=True
        )

        current_exposure = exposure_result[0].total_value if exposure_result and exposure_result[0].total_value else 0
        max_exposure = settings.modal_total * (settings.max_exposure_percent / 100)

        if current_exposure > max_exposure:
            message = (
                f"Total portfolio exposure exceeded. Current: {current_exposure}, "
                f"Limit: {max_exposure}"
            )
            send_telegram_notification(message)

    except Exception as e:
        frappe.log_error(f"check_intraday_conditions failed: {e}", "FD-Trade Scheduled Tasks")


def daily_review_notification():
    """Send daily trading review summary at market close (16:00, Mon-Fri).

    Includes: trade count, wins, losses, total P&L, system compliance rate.
    """
    try:
        today_date = today()

        todays_trades = frappe.db.get_list(
            "Trade Journal",
            filters={
                "date": today_date,
                "status": "Closed"
            },
            fields=["result_r", "result_rp", "followed_system"]
        )

        if not todays_trades:
            return

        count = len(todays_trades)
        wins = sum(1 for t in todays_trades if t.result_r and t.result_r > 0)
        losses = sum(1 for t in todays_trades if t.result_r and t.result_r < 0)
        total_pnl = sum(t.result_rp for t in todays_trades if t.result_rp)
        followed_count = sum(1 for t in todays_trades if t.followed_system)
        compliance_rate = (followed_count / count * 100) if count > 0 else 0

        message = (
            f"Daily Trading Review ({today_date})\n"
            f"Trades: {count}\n"
            f"Wins: {wins}\n"
            f"Losses: {losses}\n"
            f"Total P&L: {total_pnl}\n"
            f"System Compliance: {compliance_rate:.1f}%"
        )

        send_telegram_notification(message)

    except Exception as e:
        frappe.log_error(f"daily_review_notification failed: {e}", "FD-Trade Scheduled Tasks")


def weekly_review_notification():
    """Send weekly trading review summary on Friday at 17:00.

    Includes: total trades, win rate, total R, max drawdown, FOMO count, revenge count.
    """
    try:
        monday = get_monday_of_current_week()

        weekly_trades = frappe.db.get_list(
            "Trade Journal",
            filters={
                "date": [">=", monday],
                "status": "Closed"
            },
            fields=["result_r", "fomo", "revenge"]
        )

        if not weekly_trades:
            return

        count = len(weekly_trades)
        wins = sum(1 for t in weekly_trades if t.result_r and t.result_r > 0)
        win_rate = (wins / count * 100) if count > 0 else 0
        total_r = sum(t.result_r for t in weekly_trades if t.result_r)
        fomo_count = sum(1 for t in weekly_trades if t.fomo)
        revenge_count = sum(1 for t in weekly_trades if t.revenge)

        # Calculate max intraweek drawdown (simplified)
        running_pnl = 0
        max_drawdown = 0
        for trade in weekly_trades:
            if trade.result_r:
                running_pnl += trade.result_r
                if running_pnl < max_drawdown:
                    max_drawdown = running_pnl

        message = (
            f"Weekly Trading Review\n"
            f"Trades: {count}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Total R: {total_r:.2f}\n"
            f"Max Drawdown: {max_drawdown:.2f}R\n"
            f"FOMO Trades: {fomo_count}\n"
            f"Revenge Trades: {revenge_count}"
        )

        send_telegram_notification(message)

    except Exception as e:
        frappe.log_error(f"weekly_review_notification failed: {e}", "FD-Trade Scheduled Tasks")


def monthly_circuit_breaker_check():
    """Check monthly circuit breaker on the 1st of each month at 08:00.

    If monthly loss limit is breached, send urgent notification recommending
    system review / paper trading pause.
    """
    try:
        first_day = getdate(today()).replace(day=1)

        monthly_result = frappe.db.sql(
            """
            SELECT SUM(result_rp) as total_pnl
            FROM `tabTrade Journal`
            WHERE date >= %s AND status = 'Closed'
            """,
            (first_day,),
            as_dict=True
        )

        total_pnl = monthly_result[0].total_pnl if monthly_result and monthly_result[0].total_pnl else 0

        settings = frappe.get_single("Trading Account Settings")
        circuit_breaker_limit = settings.modal_total * (settings.monthly_circuit_breaker_percent / 100)

        if total_pnl <= -circuit_breaker_limit:
            message = (
                f"URGENT: Monthly circuit breaker breached! "
                f"Total P&L: {total_pnl}, Limit: {circuit_breaker_limit}. "
                f"Recommend full system review and paper trading pause."
            )
            send_telegram_notification(message)

    except Exception as e:
        frappe.log_error(f"monthly_circuit_breaker_check failed: {e}", "FD-Trade Scheduled Tasks")


def get_monday_of_current_week():
    """Get the Monday of the current week."""
    today_date = getdate(today())
    day_of_week = today_date.weekday()  # Monday is 0, Sunday is 6
    monday = add_to_date(today_date, days=-day_of_week)
    return monday


def check_price_alerts():
    """Cek semua Price Alert dengan status Active, bandingkan dengan harga
    current (via yfinance, delay 15-20 menit), kirim notifikasi Telegram
    jika kondisi trigger terpenuhi.

    Berjalan setiap 15 menit selama jam bursa (9-16, Senin-Jumat).
    """
    from fd_trade.utils.price_data import get_current_price

    try:
        active_alerts = frappe.get_all(
            "Price Alert",
            filters={"status": "Active"},
            fields=["name", "ticker", "alert_type", "trigger_price", "condition", "linked_trade"]
        )

        for alert in active_alerts:
            current_price = get_current_price(alert.ticker)

            if current_price is None:
                continue

            triggered = False
            if alert.condition == ">=" and current_price >= alert.trigger_price:
                triggered = True
            elif alert.condition == "<=" and current_price <= alert.trigger_price:
                triggered = True

            if triggered:
                risk_lines = ""
                if alert.linked_trade:
                    trade = frappe.db.get_value(
                        "Trade Journal", alert.linked_trade,
                        ["entry_price", "position_lot", "risk_amount"],
                        as_dict=True
                    )
                    if trade and trade.entry_price and trade.position_lot:
                        unrealized_pnl = (current_price - trade.entry_price) * trade.position_lot * 100
                        risk_status = "N/A"
                        if trade.risk_amount:
                            pct_of_risk = (unrealized_pnl / trade.risk_amount) * 100
                            risk_status = f"{pct_of_risk:+.0f}% dari risk plan"
                        risk_lines = (
                            f"Entry: Rp{trade.entry_price:,.0f} | Lot: {trade.position_lot}\n"
                            f"Unrealized P&L jika exit sekarang: Rp{unrealized_pnl:,.0f} ({risk_status})\n"
                        )

                message = (
                    f"\U0001F514 PRICE ALERT: {alert.ticker}\n"
                    f"Type: {alert.alert_type}\n"
                    f"Trigger: Rp{alert.trigger_price:,.0f} | Current: Rp{current_price:,.0f}\n"
                    f"Linked Trade: {alert.linked_trade}\n"
                    f"{risk_lines}"
                    f"(Catatan: harga yfinance delay 15-20 menit, konfirmasi manual sebelum eksekusi)"
                )
                send_telegram_notification(message)

                frappe.db.set_value("Price Alert", alert.name, {
                    "status": "Triggered",
                    "triggered_at": frappe.utils.now()
                })
                frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"check_price_alerts failed: {e}", "FD-Trade Scheduled Tasks")


def refresh_all_watchlist():
    """Auto-refresh current price, OHLC, dan Support/Resistance untuk SEMUA
    entry Watchlist, via yfinance (delay 15-20 menit).

    Job terpisah dari check_price_alerts/check_intraday_conditions supaya
    kalau ada masalah di salah satu job, job lain tetap jalan normal.
    Berjalan setiap 15 menit selama jam bursa (9-16, Senin-Jumat), offset
    1 menit dari job Price Alert supaya tidak rebutan slot yang sama.
    """
    from fd_trade.utils.price_data import get_current_price, get_current_ohlc, get_support_resistance

    try:
        tickers = frappe.get_all("Watchlist", fields=["name", "ticker"])

        updated = 0
        skipped = 0

        for row in tickers:
            if not row.ticker:
                skipped += 1
                continue

            try:
                values = {}

                price = get_current_price(row.ticker)
                if price is not None:
                    values["current_price"] = price

                ohlc = get_current_ohlc(row.ticker)
                if ohlc:
                    values["open_price"] = ohlc["open"]
                    values["high_price"] = ohlc["high"]
                    values["low_price"] = ohlc["low"]
                    values["close_price"] = ohlc["close"]

                sr_result = get_support_resistance(row.ticker)
                if sr_result:
                    values["support_level"] = sr_result["support_level"]
                    values["support_level_2"] = sr_result["support_level_2"]
                    values["support_level_3"] = sr_result["support_level_3"]
                    values["resistance_level"] = sr_result["resistance_level"]
                    values["resistance_level_2"] = sr_result["resistance_level_2"]
                    values["resistance_level_3"] = sr_result["resistance_level_3"]
                    values["sr_details"] = sr_result["details"]
                    values["trend_status"] = sr_result.get("trend")

                if values:
                    values["last_updated"] = frappe.utils.now()
                    frappe.db.set_value("Watchlist", row.name, values)
                    updated += 1

                    from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import create_signal
                    create_signal(
                        watchlist_name=row.name,
                        ticker=row.ticker,
                        current_price=values.get("current_price"),
                        trend_status=values.get("trend_status"),
                        support_level=values.get("support_level"),
                        support_level_2=values.get("support_level_2"),
                        resistance_level=values.get("resistance_level"),
                        support_level_3=values.get("support_level_3"),
                        resistance_level_2=values.get("resistance_level_2"),
                        resistance_level_3=values.get("resistance_level_3"),
                    )
                else:
                    skipped += 1

            except Exception as row_error:
                frappe.log_error(
                    f"refresh_all_watchlist failed for {row.ticker}: {row_error}",
                    "FD-Trade Scheduled Tasks"
                )
                skipped += 1
                continue

        frappe.db.commit()
        frappe.logger().info(f"refresh_all_watchlist done. Updated: {updated}, Skipped: {skipped}")

    except Exception as e:
        frappe.log_error(f"refresh_all_watchlist failed: {e}", "FD-Trade Scheduled Tasks")


def refresh_open_trades_sr():
    """Auto-refresh Support/Resistance untuk semua Trade Journal berstatus
    Open, via yfinance (delay 15-20 menit).

    Job terpisah dari refresh_all_watchlist/check_price_alerts/
    check_intraday_conditions supaya independen satu sama lain.
    Berjalan setiap 30 menit selama jam bursa (9-16, Senin-Jumat).
    """
    from fd_trade.utils.price_data import get_support_resistance

    try:
        open_trades = frappe.get_all(
            "Trade Journal",
            filters={"status": "Open"},
            fields=["name", "ticker"]
        )

        updated = 0
        skipped = 0

        for row in open_trades:
            if not row.ticker:
                skipped += 1
                continue

            try:
                result = get_support_resistance(row.ticker)
                if result:
                    frappe.db.set_value("Trade Journal", row.name, {
                        "support_level": result["support_level"],
                        "support_level_2": result["support_level_2"],
                        "support_level_3": result["support_level_3"],
                        "resistance_level": result["resistance_level"],
                        "resistance_level_2": result["resistance_level_2"],
                        "resistance_level_3": result["resistance_level_3"],
                        "sr_details": result["details"],
                    })
                    updated += 1
                else:
                    skipped += 1
            except Exception as row_error:
                frappe.log_error(
                    f"refresh_open_trades_sr failed for {row.ticker}: {row_error}",
                    "FD-Trade Scheduled Tasks"
                )
                skipped += 1
                continue

        frappe.db.commit()
        frappe.logger().info(f"refresh_open_trades_sr done. Updated: {updated}, Skipped: {skipped}")

    except Exception as e:
        frappe.log_error(f"refresh_open_trades_sr failed: {e}", "FD-Trade Scheduled Tasks")


@frappe.whitelist()
def refresh_all_watchlist_now():
    """Wrapper whitelisted supaya refresh_all_watchlist() bisa dipanggil
    manual dari tombol UI List View, bukan cuma dari scheduler."""
    refresh_all_watchlist()
    return {"status": "done"}


def refresh_ihsg_trend():
    """Update trend IHSG (^JKSE) sebagai acuan kondisi market secara umum.
    Disimpan di Trading Account Settings (Single), field ihsg_*.
    Terpisah dari refresh_all_watchlist supaya tidak saling mengganggu."""
    from fd_trade.utils.price_data import get_current_price, get_support_resistance, calculate_market_regime

    try:
        price = get_current_price("^JKSE")
        result = get_support_resistance("^JKSE")

        settings = frappe.get_single("Trading Account Settings")
        previous = frappe.get_all("IHSG Signal", fields=["market_regime"], order_by="creation desc", limit=1)
        regime = None
        if price is not None:
            settings.ihsg_current_price = price
        if result:
            settings.ihsg_trend = result.get("trend")
            settings.ihsg_ma20 = result.get("ma20")
            settings.ihsg_ma50 = result.get("ma50")
            regime = calculate_market_regime(
                result.get("trend"), price, result.get("ma20"), result.get("ma50")
            )
        settings.ihsg_last_updated = frappe.utils.now()
        settings.save(ignore_permissions=True)
        if result and regime:
            ihsg_signal = frappe.get_doc({
                "doctype": "IHSG Signal",
                "timestamp": frappe.utils.now(),
                "ihsg_price": price,
                "trend_status": result.get("trend"),
                "market_regime": regime,
                "support_level": result.get("support_level"),
                "resistance_level": result.get("resistance_level"),
                "notes": f"Regime IHSG saat ini: {regime}.",
            })
            ihsg_signal.insert(ignore_permissions=True)
            if previous and previous[0].market_regime != regime:
                send_telegram_notification(f"Market regime IHSG berubah: {previous[0].market_regime} -> {regime}.")
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"refresh_ihsg_trend failed: {e}", "FD-Trade IHSG")


@frappe.whitelist()
def refresh_ihsg_trend_now():
    """Wrapper whitelisted untuk dipanggil manual dari tombol UI."""
    refresh_ihsg_trend()
    return {"status": "done"}


def cleanup_old_watchlist_signals():
    """Hapus record Watchlist Signal yang lebih tua dari 60 hari, supaya
    tabel histori tidak membengkak tanpa batas. Jalan sekali sehari,
    setelah jam bursa tutup."""
    try:
        cutoff = frappe.utils.add_days(frappe.utils.now(), -60)
        old_signals = frappe.get_all(
            "Watchlist Signal",
            filters={"timestamp": ["<", cutoff]},
            pluck="name"
        )
        for name in old_signals:
            frappe.delete_doc("Watchlist Signal", name, ignore_permissions=True, force=True)

        frappe.db.commit()
        frappe.logger().info(f"cleanup_old_watchlist_signals done. Dihapus: {len(old_signals)} record.")

    except Exception as e:
        frappe.log_error(f"cleanup_old_watchlist_signals failed: {e}", "FD-Trade Scheduled Tasks")


def cleanup_old_ihsg_signals():
    """Hapus histori IHSG Signal yang melewati retention days."""
    try:
        settings = frappe.get_single("Trading Account Settings")
        days = settings.ihsg_signal_retention_days or 90
        cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -days)
        old_signals = frappe.get_all("IHSG Signal", filters=[["timestamp", "<", cutoff]], pluck="name")
        for name in old_signals:
            frappe.delete_doc("IHSG Signal", name, ignore_permissions=True, force=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"cleanup_old_ihsg_signals failed: {e}", "FD-Trade Scheduled Tasks")
