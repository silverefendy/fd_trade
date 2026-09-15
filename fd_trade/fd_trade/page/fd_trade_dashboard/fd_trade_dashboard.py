import frappe

@frappe.whitelist()
def get_dashboard_data():
    settings = frappe.get_single("Trading Account Settings")

    open_positions = frappe.get_all(
        "Trade Journal",
        filters={"status": "Open"},
        fields=["name", "ticker", "entry_price", "stop_loss", "position_lot",
                "target_price", "risk_amount", "date"],
        order_by="date desc"
    )

    watchlist = frappe.get_all(
        "Watchlist",
        fields=["name", "ticker", "tier", "sector", "support_level", "resistance_level"],
        order_by="tier asc"
    )

    total_exposure = 0
    for p in open_positions:
        if p.entry_price and p.position_lot:
            total_exposure += p.entry_price * p.position_lot * 100

    return {
        "modal_total": settings.modal_total or 0,
        "total_exposure": total_exposure,
        "open_positions": open_positions,
        "watchlist": watchlist,
        "open_count": len(open_positions),
        "watchlist_count": len(watchlist),
    }
