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
        weekly_trades = frappe.db.get_list(
            "Trade Journal",
            filters={
                "date": [">=", monday],
                "status": "Closed"
            },
            fields=["SUM(result_rp) as total_pnl"]
        )

        weekly_pnl = weekly_trades[0].total_pnl if weekly_trades and weekly_trades[0].total_pnl else 0
        weekly_loss_limit = settings.modal_total * (settings.weekly_loss_limit_percent / 100)

        if weekly_pnl <= -weekly_loss_limit:
            message = (
                f"Weekly loss limit breached. Current P&L: {weekly_pnl}. "
                f"Recommend 50% size reduction."
            )
            send_telegram_notification(message)

        # Check total open exposure
        total_exposure = frappe.db.get_list(
            "Trade Journal",
            filters={"status": "Open"},
            fields=["SUM(entry_price * position_lot * 100) as total_value"]
        )

        current_exposure = total_exposure[0].total_value if total_exposure and total_exposure[0].total_value else 0
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
            f"Daily Trading Review ({today_date})\\n"
            f"Trades: {count}\\n"
            f"Wins: {wins}\\n"
            f"Losses: {losses}\\n"
            f"Total P&L: {total_pnl}\\n"
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
            f"Weekly Trading Review\\n"
            f"Trades: {count}\\n"
            f"Win Rate: {win_rate:.1f}%\\n"
            f"Total R: {total_r:.2f}\\n"
            f"Max Drawdown: {max_drawdown:.2f}R\\n"
            f"FOMO Trades: {fomo_count}\\n"
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

        monthly_trades = frappe.db.get_list(
            "Trade Journal",
            filters={
                "date": [">=", first_day],
                "status": "Closed"
            },
            fields=["SUM(result_rp) as total_pnl"]
        )

        if not monthly_trades:
            return

        total_pnl = monthly_trades[0].total_pnl if monthly_trades[0].total_pnl else 0

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
    from fd_trade.utils.telegram import send_telegram_notification

    try:
        active_alerts = frappe.get_all(
            "Price Alert",
            filters={"status": "Active"},
            fields=["name", "ticker", "alert_type", "trigger_price", "condition", "linked_trade"]
        )

        for alert in active_alerts:
            current_price = get_current_price(alert.ticker)

            if current_price is None:
                # Gagal ambil harga (network/ticker salah), skip, jangan crash job.
                continue

            triggered = False
            if alert.condition == ">=" and current_price >= alert.trigger_price:
                triggered = True
            elif alert.condition == "<=" and current_price <= alert.trigger_price:
                triggered = True

            if triggered:
                message = (
                    f"\U0001F514 PRICE ALERT: {alert.ticker}\n"
                    f"Type: {alert.alert_type}\n"
                    f"Trigger: Rp{alert.trigger_price:,.0f} | Current: Rp{current_price:,.0f}\n"
                    f"Linked Trade: {alert.linked_trade}\n"
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
