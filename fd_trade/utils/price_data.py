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
