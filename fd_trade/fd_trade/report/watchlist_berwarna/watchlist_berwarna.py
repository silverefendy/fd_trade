import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Ticker", "fieldname": "ticker", "fieldtype": "Link", "options": "Watchlist", "width": 100},
        {"label": "Sector", "fieldname": "sector", "fieldtype": "Data", "width": 160},
        {"label": "Tier", "fieldname": "tier", "fieldtype": "Data", "width": 70},
        {"label": "Stock Group", "fieldname": "stock_group", "fieldtype": "Link", "options": "Stock Group", "width": 130},
        {"label": "Current Price", "fieldname": "current_price", "fieldtype": "Currency", "width": 120},
        {"label": "High", "fieldname": "high_price", "fieldtype": "Currency", "width": 110},
        {"label": "Low", "fieldname": "low_price", "fieldtype": "Currency", "width": 110},
        {"label": "Support 01", "fieldname": "support_level", "fieldtype": "Currency", "width": 110},
        {"label": "Resist 01", "fieldname": "resistance_level", "fieldtype": "Currency", "width": 110},
        {"label": "Support 02", "fieldname": "support_level_2", "fieldtype": "Currency", "width": 110},
        {"label": "Resist 02", "fieldname": "resistance_level_2", "fieldtype": "Currency", "width": 110},
        {"label": "Last Updated", "fieldname": "last_updated", "fieldtype": "Datetime", "width": 160},
    ]


def get_data(filters):
    filters = filters or {}
    conditions = []
    values = {}

    if filters.get("sector"):
        conditions.append("sector = %(sector)s")
        values["sector"] = filters["sector"]

    if filters.get("tier"):
        conditions.append("tier = %(tier)s")
        values["tier"] = filters["tier"]

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    return frappe.db.sql(
        f"""
        SELECT
            ticker, sector, tier, stock_group, current_price,
            high_price, low_price,
            support_level, resistance_level,
            support_level_2, resistance_level_2,
            last_updated
        FROM `tabWatchlist`
        {where_clause}
        ORDER BY ticker ASC
        """,
        values,
        as_dict=True,
    )
