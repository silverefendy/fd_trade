"""
Volume Profile Utility Module
Hitung distribusi volume per level harga dari data Price History yang
sudah tersimpan di database, dipakai sebagai pengganti Support/Resistance
berbasis swing high/low murni (keputusan 20 Sep 2026: Opsi A, baca dari
Price History table -- bukan fetch live yfinance terpisah).

Pendekatan: karena Price History cuma OHLCV harian (bukan tick-by-tick),
volume tiap hari disebar RATA ke semua bin harga yang overlap dengan
rentang [low, high] hari itu -- pendekatan standar Volume Profile
berbasis data harian.
"""

import frappe

NUM_BINS = 50
LOOKBACK_DAYS = 180  # hari kalender, ~120 hari bursa
VALUE_AREA_PCT = 0.70  # standar Volume Profile: 70% volume di sekitar POC
MIN_ROWS_REQUIRED = 30


def get_price_history_rows(ticker, lookback_days=LOOKBACK_DAYS, end_date=None):
    """Ambil baris Price History (Daily) utk ticker, urut tanggal naik.

    end_date opsional -- kalau diisi, hitung "as of" tanggal itu (utk
    backtest validasi historis), bukan selalu sampai hari ini.
    """
    filters = {"ticker": ticker, "timeframe": "Daily"}
    if end_date:
        filters["date"] = ["<=", end_date]
    rows = frappe.get_all(
        "Price History",
        filters=filters,
        fields=["date", "open", "high", "low", "close", "volume"],
        order_by="date desc",
        limit_page_length=lookback_days,
    )
    return list(reversed(rows))  # kronologis naik


def calculate_volume_profile(ticker, current_price=None, lookback_days=LOOKBACK_DAYS,
                              num_bins=NUM_BINS, end_date=None, rows=None):
    """Hitung Volume Profile: Point of Control (POC), Value Area, dan
    kandidat Support/Resistance dari High Volume Node (HVN).

    ``rows`` opsional -- kalau caller sudah punya baris Price History
    (misal dari get_support_resistance), reuse di sini alih-alih query
    ulang ke database.

    Returns dict atau None kalau data tidak cukup (< MIN_ROWS_REQUIRED hari).
    """
    if rows is None:
        rows = get_price_history_rows(ticker, lookback_days, end_date)

    if len(rows) < MIN_ROWS_REQUIRED:
        frappe.log_error(
            f"Data Price History tidak cukup utk Volume Profile {ticker} ({len(rows)} baris)",
            "FD-Trade Volume Profile",
        )
        return None

    all_highs = [r["high"] for r in rows if r.get("high")]
    all_lows = [r["low"] for r in rows if r.get("low")]
    if not all_highs or not all_lows:
        return None

    price_min = min(all_lows)
    price_max = max(all_highs)
    if price_max <= price_min:
        return None

    bin_size = (price_max - price_min) / num_bins
    bin_volumes = [0.0] * num_bins

    def bin_index(price):
        idx = int((price - price_min) / bin_size)
        return max(0, min(num_bins - 1, idx))

    for row in rows:
        low, high, volume = row.get("low"), row.get("high"), row.get("volume") or 0
        if not low or not high or high <= low or volume <= 0:
            continue
        start_bin, end_bin = bin_index(low), bin_index(high)
        span = end_bin - start_bin + 1
        vol_per_bin = volume / span
        for b in range(start_bin, end_bin + 1):
            bin_volumes[b] += vol_per_bin

    total_volume = sum(bin_volumes)
    if total_volume <= 0:
        return None

    poc_index = max(range(num_bins), key=lambda i: bin_volumes[i])
    poc_price = price_min + (poc_index + 0.5) * bin_size

    va_volume = bin_volumes[poc_index]
    lo, hi = poc_index, poc_index
    while va_volume / total_volume < VALUE_AREA_PCT and (lo > 0 or hi < num_bins - 1):
        vol_below = bin_volumes[lo - 1] if lo > 0 else -1
        vol_above = bin_volumes[hi + 1] if hi < num_bins - 1 else -1
        if vol_above >= vol_below:
            hi += 1
            va_volume += bin_volumes[hi]
        else:
            lo -= 1
            va_volume += bin_volumes[lo]

    value_area_low = price_min + lo * bin_size
    value_area_high = price_min + (hi + 1) * bin_size

    if current_price is None:
        current_price = rows[-1]["close"]

    nonzero = [(i, v) for i, v in enumerate(bin_volumes) if v > 0]
    sorted_vols = sorted((v for _, v in nonzero), reverse=True)
    cut_index = max(0, len(sorted_vols) // 3 - 1)
    threshold = sorted_vols[cut_index] if sorted_vols else 0
    hvn_prices = [price_min + (i + 0.5) * bin_size for i, v in nonzero if v >= threshold]

    def dedupe(values, pct=0.01):
        result = []
        for v in values:
            if not result or abs(v - result[-1]) / result[-1] > pct:
                result.append(v)
        return result

    supports = dedupe(sorted([p for p in hvn_prices if p < current_price], reverse=True))
    resistances = dedupe(sorted([p for p in hvn_prices if p > current_price]))

    return {
        "poc": round(poc_price, 2),
        "value_area_high": round(value_area_high, 2),
        "value_area_low": round(value_area_low, 2),
        "support_level": supports[0] if len(supports) > 0 else None,
        "support_level_2": supports[1] if len(supports) > 1 else None,
        "support_level_3": supports[2] if len(supports) > 2 else None,
        "resistance_level": resistances[0] if len(resistances) > 0 else None,
        "resistance_level_2": resistances[1] if len(resistances) > 1 else None,
        "resistance_level_3": resistances[2] if len(resistances) > 2 else None,
        "bins": [
            {
                "price_low": round(price_min + i * bin_size, 2),
                "price_high": round(price_min + (i + 1) * bin_size, 2),
                "volume": round(bin_volumes[i], 0),
            }
            for i in range(num_bins)
        ],
        "total_volume": round(total_volume, 0),
        "rows_used": len(rows),
    }
