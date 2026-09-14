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
        full_ticker = f"{ticker}.JK"

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


def get_support_resistance(ticker):
    """Hitung level support & resistance kombinasi Swing High/Low + Moving Average.

    Menggunakan histori 6 bulan harian. Swing point dideteksi dengan window
    5 hari kiri-kanan (titik balik lokal). MA yang dipakai: MA20, MA50, MA200.

    Returns:
        dict dengan keys: support_level, resistance_level, details (str)
        atau None jika data tidak cukup / gagal fetch.
    """
    try:
        full_ticker = f"{ticker}.JK"
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

        resistances_above = sorted(h for h in swing_highs if h > current_price)
        supports_below = sorted((l for l in swing_lows if l < current_price), reverse=True)

        swing_resistance = resistances_above[0] if resistances_above else None
        swing_support = supports_below[0] if supports_below else None

        support_candidates = [v for v in [swing_support, ma20, ma50, ma200] if v is not None and v < current_price]
        resistance_candidates = [v for v in [swing_resistance, ma20, ma50, ma200] if v is not None and v > current_price]

        support_level = max(support_candidates) if support_candidates else None
        resistance_level = min(resistance_candidates) if resistance_candidates else None

        detail_lines = [f"Current Price: Rp{current_price:,.0f}"]
        if swing_support:
            detail_lines.append(f"Swing Support: Rp{swing_support:,.0f}")
        if swing_resistance:
            detail_lines.append(f"Swing Resistance: Rp{swing_resistance:,.0f}")
        if ma20:
            detail_lines.append(f"MA20: Rp{ma20:,.0f}")
        if ma50:
            detail_lines.append(f"MA50: Rp{ma50:,.0f}")
        if ma200:
            detail_lines.append(f"MA200: Rp{ma200:,.0f}")

        return {
            "support_level": support_level,
            "resistance_level": resistance_level,
            "details": "\n".join(detail_lines),
        }

    except Exception as e:
        frappe.log_error(f"get_support_resistance failed for {ticker}: {e}", "FD-Trade Price Data")
        return None
