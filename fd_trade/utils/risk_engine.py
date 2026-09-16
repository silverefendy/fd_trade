"""
Risk Engine — satu-satunya sumber kebenaran untuk perhitungan position
sizing di seluruh app (Trade Journal, Watchlist Signal, dan modul lain
yang butuh saran lot/alokasi dana).

Semua satuan "lot" di sini konsisten = 100 lembar (standar BEI), BUKAN
jumlah lembar mentah. Ini menyamakan konvensi Trade Journal yang sudah
ada sejak awal.
"""

import frappe


def get_open_exposure(ticker=None, exclude_docname=None):
    """Hitung total nilai posisi Open di Trade Journal.

    Args:
        ticker: kalau diisi, hitung juga eksposur khusus ticker itu.
        exclude_docname: docname Trade Journal yang dikecualikan dari
            perhitungan -- WAJIB diisi saat menghitung ulang untuk trade
            yang SUDAH Open (misal saat edit), supaya trade itu sendiri
            tidak dihitung dobel sebagai "eksposur existing".

    Returns:
        tuple (per_stock_value, total_value) dalam Rupiah.
    """
    conditions = "status = 'Open'"
    params = []

    if exclude_docname:
        conditions += " AND name != %s"
        params.append(exclude_docname)

    total_result = frappe.db.sql(
        f"""
        SELECT SUM(entry_price * position_lot * 100) as total_value
        FROM `tabTrade Journal`
        WHERE {conditions}
        """,
        params,
        as_dict=True
    )
    total_value = total_result[0].total_value or 0

    per_stock_value = 0
    if ticker:
        stock_conditions = conditions + " AND ticker = %s"
        stock_params = params + [ticker]
        stock_result = frappe.db.sql(
            f"""
            SELECT SUM(entry_price * position_lot * 100) as total_value
            FROM `tabTrade Journal`
            WHERE {stock_conditions}
            """,
            stock_params,
            as_dict=True
        )
        per_stock_value = stock_result[0].total_value or 0

    return per_stock_value, total_value


def calculate_position_sizing(ticker, current_price, risk_per_share, settings=None, exclude_docname=None):
    """Hitung saran lot & alokasi dana, mempertimbangkan SEMUA batasan
    yang dikonfigurasi di Trading Account Settings sekaligus -- bukan
    cuma risk_per_trade_percent saja.

    Returns:
        dict lengkap dengan angka & alasan pembatas (limiting_factor),
        atau None kalau data tidak cukup untuk dihitung.
    """
    if not current_price or not risk_per_share or risk_per_share <= 0:
        return None

    if settings is None:
        settings = frappe.get_single("Trading Account Settings")

    modal_total = settings.modal_total or 0
    risk_pct = settings.risk_per_trade_percent or 0
    max_per_stock_pct = settings.max_per_stock_percent or 0
    max_exposure_pct = settings.max_exposure_percent or 0

    if not modal_total:
        return None

    # 1. Batasan dari risk per trade (rumus lama)
    risk_amount = modal_total * (risk_pct / 100)
    lot_by_risk = int(risk_amount / risk_per_share / 100)

    # 2. Batasan dari sisa kuota per-saham
    per_stock_exposure, total_exposure = get_open_exposure(ticker, exclude_docname)
    max_per_stock_rp = modal_total * (max_per_stock_pct / 100) if max_per_stock_pct else modal_total
    remaining_per_stock = max(0, max_per_stock_rp - per_stock_exposure)
    lot_by_max_per_stock = int(remaining_per_stock / current_price / 100)

    # 3. Batasan dari sisa kuota total eksposur portofolio
    max_exposure_rp = modal_total * (max_exposure_pct / 100) if max_exposure_pct else modal_total
    remaining_exposure = max(0, max_exposure_rp - total_exposure)
    lot_by_max_exposure = int(remaining_exposure / current_price / 100)

    candidates = {
        "risk": lot_by_risk,
        "max_per_stock": lot_by_max_per_stock,
        "max_exposure": lot_by_max_exposure,
    }
    final_lot = max(min(candidates.values()), 0)
    limiting_factor = min(candidates, key=candidates.get)

    return {
        "risk_amount": risk_amount,
        "risk_per_share": risk_per_share,
        "lot_by_risk": lot_by_risk,
        "lot_by_max_per_stock": lot_by_max_per_stock,
        "lot_by_max_exposure": lot_by_max_exposure,
        "final_lot": final_lot,
        "limiting_factor": limiting_factor,
        "suggested_position_rp": final_lot * 100 * current_price,
    }
