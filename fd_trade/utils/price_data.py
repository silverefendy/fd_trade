"""
Price Data Utility Module
Fetches stock price data using yfinance for IDX tickers.
"""

import yfinance as yf
import frappe


def get_current_price(ticker):
    """Fetch latest available price for an IDX ticker using yfinance.

    Ticker should be passed without suffix (e.g. 'BBCA'); this function
    appends '.JK' automatically. Returns None and logs error on failure
    rather than raising, since this is best-effort delayed data (15-20 min).

    Args:
        ticker (str): IDX ticker symbol without .JK suffix

    Returns:
        float: Latest available price, or None if fetch fails
    """
    try:
        # Append .JK suffix for IDX tickers
        full_ticker = ticker if ticker.startswith("^") else f"{ticker}.JK"

        # Fetch data
        stock = yf.Ticker(full_ticker)
        hist = stock.history(period="1d")

        if hist.empty:
            frappe.log_error(f"No data found for ticker {full_ticker}", "FD-Trade Price Data")
            return None

        # Return the latest close price
        latest_price = hist['Close'].iloc[-1]
        return float(latest_price)

    except Exception as e:
        frappe.log_error(f"Failed to fetch price for {ticker}: {e}", "FD-Trade Price Data")
        return None


def get_current_ohlc(ticker):
    """Ambil Open/High/Low/Close hari terakhir untuk ticker IDX.

    Returns:
        dict dengan keys: open, high, low, close -- atau None jika gagal.
    """
    try:
        full_ticker = ticker if ticker.startswith("^") else f"{ticker}.JK"
        stock = yf.Ticker(full_ticker)
        hist = stock.history(period="1d")

        if hist.empty:
            frappe.log_error(f"No OHLC data for ticker {full_ticker}", "FD-Trade Price Data")
            return None

        last = hist.iloc[-1]
        return {
            "open": float(last["Open"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "close": float(last["Close"]),
        }
    except Exception as e:
        frappe.log_error(f"Failed to fetch OHLC for {ticker}: {e}", "FD-Trade Price Data")
        return None

def get_support_resistance(ticker):
    """Hitung 2 level support & 2 level resistance terdekat, kombinasi
    Swing High/Low + Moving Average.

    Menggunakan histori 6 bulan harian. Swing point dideteksi dengan window
    5 hari kiri-kanan (titik balik lokal). MA yang dipakai: MA20, MA50, MA200.

    Returns:
        dict dengan keys: support_level, support_level_2, resistance_level,
        resistance_level_2, details (str) -- atau None jika data tidak cukup.
    """
    try:
        full_ticker = ticker if ticker.startswith("^") else f"{ticker}.JK"
        stock = yf.Ticker(full_ticker)
        hist = stock.history(period="6mo")

        if hist.empty or len(hist) < 30:
            frappe.log_error(f"Data histori tidak cukup untuk {full_ticker}", "FD-Trade Price Data")
            return None

        current_price = float(hist["Close"].iloc[-1])

        ma20 = float(hist["Close"].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else None
        ma50 = float(hist["Close"].rolling(50).mean().iloc[-1]) if len(hist) >= 50 else None
        ma200 = float(hist["Close"].rolling(200).mean().iloc[-1]) if len(hist) >= 200 else None

        window = 5
        highs = hist["High"].values
        lows = hist["Low"].values
        swing_highs, swing_lows = [], []

        for i in range(window, len(highs) - window):
            seg_h = highs[i - window:i + window + 1]
            if highs[i] == max(seg_h):
                swing_highs.append(float(highs[i]))
            seg_l = lows[i - window:i + window + 1]
            if lows[i] == min(seg_l):
                swing_lows.append(float(lows[i]))

        ma_values = [v for v in [ma20, ma50, ma200] if v is not None]

        # Gabungkan semua kandidat, hilangkan duplikat yang terlalu berdekatan (<0.5% beda)
        def dedupe(values):
            values = sorted(set(values))
            result = []
            for v in values:
                if not result or abs(v - result[-1]) / result[-1] > 0.005:
                    result.append(v)
            return result

        support_candidates = dedupe([v for v in (swing_lows + ma_values) if v < current_price])
        resistance_candidates = dedupe([v for v in (swing_highs + ma_values) if v > current_price])

        # Support: urut dari yang PALING DEKAT (tertinggi) ke yang lebih jauh
        support_candidates = sorted(support_candidates, reverse=True)
        # Resistance: urut dari yang PALING DEKAT (terendah) ke yang lebih jauh
        resistance_candidates = sorted(resistance_candidates)

        support_level = support_candidates[0] if len(support_candidates) > 0 else 0
        support_level_2 = support_candidates[1] if len(support_candidates) > 1 else 0
        resistance_level = resistance_candidates[0] if len(resistance_candidates) > 0 else 0
        resistance_level_2 = resistance_candidates[1] if len(resistance_candidates) > 1 else 0

        detail_lines = [f"Current Price: Rp{current_price:,.0f}"]
        if swing_lows:
            nearest_swing_low = max([v for v in swing_lows if v < current_price], default=None)
            if nearest_swing_low:
                detail_lines.append(f"Swing Support: Rp{nearest_swing_low:,.0f}")
        if swing_highs:
            nearest_swing_high = min([v for v in swing_highs if v > current_price], default=None)
            if nearest_swing_high:
                detail_lines.append(f"Swing Resistance: Rp{nearest_swing_high:,.0f}")
        if ma20:
            detail_lines.append(f"MA20: Rp{ma20:,.0f}")
        if ma50:
            detail_lines.append(f"MA50: Rp{ma50:,.0f}")
        if ma200:
            detail_lines.append(f"MA200: Rp{ma200:,.0f}")

        # Trend classification (5 kategori) berdasarkan selisih MA20 vs MA50,
        # dikonfirmasi posisi current_price terhadap MA20. Ini deskripsi
        # kondisi teknikal SAAT INI, bukan prediksi harga masa depan.
        trend = None
        if ma20 and ma50:
            ma_gap_pct = (ma20 - ma50) / ma50 * 100
            price_above_ma20 = current_price > ma20

            if ma_gap_pct > 2:
                trend = "Bullish Kuat" if price_above_ma20 else "Bullish Lemah"
            elif ma_gap_pct < -2:
                trend = "Bearish Kuat" if not price_above_ma20 else "Bearish Lemah"
            else:
                trend = "Sideways"

        return {
            "support_level": support_level,
            "support_level_2": support_level_2,
            "resistance_level": resistance_level,
            "resistance_level_2": resistance_level_2,
            "details": "\n".join(detail_lines),
            "trend": trend,
            "ma20": ma20,
            "ma50": ma50,
        }

    except Exception as e:
        frappe.log_error(f"get_support_resistance failed for {ticker}: {e}", "FD-Trade Price Data")
        return None


def calculate_recommendation(ticker, current_price, trend, support_level, support_level_2,
                              resistance_level):
    """Rule-based recommendation (Fase 1) -- BUKAN prediksi harga, murni
    penerjemahan kondisi teknikal saat ini menjadi Buy/Wait/Sell/Avoid +
    entry zone + position sizing berbasis risk management yang sudah
    dikonfigurasi di Trading Account Settings.

    Priority order (satu saham hanya dapat SATU recommendation):
    1. Trend "Bearish Kuat" -> Avoid, apapun posisi harga
    2. Dekat Support (price >= support, gap <= 2%) -> Buy + entry zone + lot
    3. Dekat Resistance (price <= resistance, gap <= 2%), trend bukan
       "Bullish Kuat" -> Sell (bukan short -- kurangi/keluar posisi jika
       sudah pegang, jangan entry baru jika belum)
    4. Selain itu -> Wait
    """
    threshold = 0.02  # 2%

    if trend == "Bearish Kuat":
        return {"recommendation": "Avoid"}

    if support_level and current_price is not None and current_price >= support_level:
        gap_pct = (current_price - support_level) / support_level
        if gap_pct <= threshold:
            result = {
                "recommendation": "Buy",
                "recommendation_price_low": support_level,
                "recommendation_price_high": support_level * 1.01,
            }
            if support_level_2:
                risk_per_share = current_price - support_level_2
                if risk_per_share > 0:
                    from fd_trade.utils.risk_engine import calculate_position_sizing
                    sizing = calculate_position_sizing(ticker, current_price, risk_per_share)
                    if sizing:
                        result["risk_amount"] = sizing["risk_amount"]
                        result["risk_per_share"] = sizing["risk_per_share"]
                        result["suggested_lot"] = sizing["final_lot"]
                        result["suggested_position_rp"] = sizing["suggested_position_rp"]
                        result["sizing_limiting_factor"] = sizing["limiting_factor"]
            return result

    if (resistance_level and current_price is not None and current_price <= resistance_level
            and trend != "Bullish Kuat"):
        gap_pct = (resistance_level - current_price) / resistance_level
        if gap_pct <= threshold:
            return {
                "recommendation": "Sell",
                "recommendation_price_low": resistance_level * 0.99,
                "recommendation_price_high": resistance_level,
            }

    return {"recommendation": "Wait"}
