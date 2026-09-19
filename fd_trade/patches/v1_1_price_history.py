"""Patch schema Price History dan tracking Watchlist."""

import frappe


def execute():
    frappe.reload_doc("fd_trade", "doctype", "price_history")
    frappe.reload_doc("fd_trade", "doctype", "watchlist")
    # Existing Watchlist records should retain the requested default behavior:
    # tracking aktif unless user explicitly turns it off afterwards.
    frappe.db.sql("UPDATE `tabWatchlist` SET track_price_history = 1 WHERE IFNULL(track_price_history, 0) = 0")
    try:
        frappe.db.add_unique(
            "Price History",
            ["ticker", "date", "timeframe"],
            "price_history_ticker_date_timeframe_unique",
        )
    except Exception as e:
        frappe.log_error(f"Price History unique index patch: {e}", "FD-Trade Price History")
