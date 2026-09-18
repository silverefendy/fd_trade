"""
Price Data Utility Module
Fetches stock price data using yfinance for IDX tickers.
"""

import yfinance as yf
import frappe


PROXIMITY_THRESHOLD_PCT = 3.0
VOLUME_HIGH_RATIO = 1.5
VOLUME_LOW_RATIO = 0.5
VOLUME_AVERAGE_DAYS = 20


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
    """Hitung 3 level support & 3 level resistance terdekat, kombinasi
    Swing High/Low + Moving Average.

    Menggunakan histori 6 bulan harian. Swing point dideteksi dengan window
    5 hari kiri-kanan (titik balik lokal). MA yang dipakai: MA20, MA50, MA200.

    Returns:
        dict dengan keys level S/R 1-3 dan details (str), atau None jika data
        tidak cukup. Key level lama adalah alias langsung S1/R1.
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

        support_levels = support_candidates[:3]
        resistance_levels = resistance_candidates[:3]

        support_level = support_levels[0] if len(support_levels) > 0 else None
        support_level_2 = support_levels[1] if len(support_levels) > 1 else None
        support_level_3 = support_levels[2] if len(support_levels) > 2 else None
        resistance_level = resistance_levels[0] if len(resistance_levels) > 0 else None
        resistance_level_2 = resistance_levels[1] if len(resistance_levels) > 1 else None
        resistance_level_3 = resistance_levels[2] if len(resistance_levels) > 2 else None

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

        # BUG FIX (17 Sep 2026): support/resistance sebelumnya bisa berisi
        # desimal panjang kalau kandidat terpilih berasal dari MA (rolling mean),
        # bukan dari swing high/low OHLC asli yang sudah bulat. Dibulatkan ke
        # fraksi harga resmi BEI supaya semua level konsisten & bisa dieksekusi.
        return {
            "support_level": round_to_tick(support_level),
            "support_level_2": round_to_tick(support_level_2),
            "support_level_3": round_to_tick(support_level_3),
            "resistance_level": round_to_tick(resistance_level),
            "resistance_level_2": round_to_tick(resistance_level_2),
            "resistance_level_3": round_to_tick(resistance_level_3),
            "details": "\n".join(detail_lines),
            "trend": trend,
            "ma20": ma20,
            "ma50": ma50,
        }

    except Exception as e:
        frappe.log_error(f"get_support_resistance failed for {ticker}: {e}", "FD-Trade Price Data")
        return None


def get_nearest_level(current_price, levels_dict, threshold_pct=PROXIMITY_THRESHOLD_PCT):
    """Tentukan level S/R terdekat dari harga sekarang.

    Return berisi nama field, harga level, jarak persen, dan kategori
    proximity. Jika tidak ada level valid atau semuanya di luar threshold,
    kategori dikembalikan sebagai ``di tengah range``.
    """
    if current_price is None or not levels_dict:
        return {
            "level_name": None, "level_price": None, "distance_pct": None,
            "category": "di tengah range",
        }

    candidates = []
    for name in ("support_level", "support_level_2", "support_level_3",
                 "resistance_level", "resistance_level_2", "resistance_level_3"):
        value = levels_dict.get(name)
        if value is not None and value > 0:
            distance_pct = abs(current_price - value) / value * 100
            candidates.append((distance_pct, name, value))

    if not candidates:
        return {
            "level_name": None, "level_price": None, "distance_pct": None,
            "category": "di tengah range",
        }

    distance_pct, level_name, level_price = min(candidates, key=lambda item: item[0])
    category = "di tengah range"
    if distance_pct <= threshold_pct:
        category = "mendekati support" if level_name.startswith("support") else "mendekati resistance"

    return {
        "level_name": level_name,
        "level_price": round_to_tick(level_price),
        "distance_pct": round(distance_pct, 2),
        "category": category,
    }


def get_volume_confirmation(ticker, history=None, high_ratio=VOLUME_HIGH_RATIO,
                            low_ratio=VOLUME_LOW_RATIO):
    """Validasi volume terakhir terhadap rata-rata volume 20 hari.

    ``history`` dapat diisi dengan histori yang sudah di-fetch caller agar
    tidak terjadi hit yfinance kedua untuk ticker yang sama.
    """
    try:
        if history is None:
            full_ticker = ticker if ticker.startswith("^") else f"{ticker}.JK"
            history = yf.Ticker(full_ticker).history(period="6mo")

        if history is None or "Volume" not in history or history.empty:
            return None

        volumes = history["Volume"].dropna()
        if len(volumes) < 2:
            return None

        current_volume = float(volumes.iloc[-1])
        baseline_values = volumes.iloc[-(VOLUME_AVERAGE_DAYS + 1):-1]
        if baseline_values.empty:
            return None
        avg_volume = float(baseline_values.mean())
        if avg_volume <= 0 or current_volume < 0:
            return None

        ratio = current_volume / avg_volume
        if ratio > high_ratio:
            status = "Volume Tinggi"
        elif ratio < low_ratio:
            status = "Volume Rendah"
        else:
            status = "Volume Normal"

        return {
            "current_volume": current_volume,
            "avg_volume_20d": avg_volume,
            "volume_status": status,
        }
    except Exception as e:
        frappe.log_error(f"get_volume_confirmation failed for {ticker}: {e}", "FD-Trade Volume")
        return None


def round_to_tick(price):
    """Bulatkan harga ke kelipatan fraksi harga resmi BEI (Kep-00023/BEI/04-2016),
    supaya angka yang disarankan benar-benar bisa dieksekusi di market -- bukan
    angka desimal yang tidak valid untuk order beli/jual.
    """
    if not price:
        return price
    if price < 200:
        tick = 1
    elif price < 500:
        tick = 2
    elif price < 2000:
        tick = 5
    elif price < 5000:
        tick = 10
    else:
        tick = 25
    return round(price / tick) * tick


def calculate_recommendation(ticker, current_price, trend, support_level, support_level_2,
                              resistance_level, support_level_3=None,
                              resistance_level_2=None, resistance_level_3=None,
                              ihsg_trend=None, proximity=None, volume_status=None):
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
    if trend == "Bearish Kuat":
        result = {"recommendation": "Avoid"}
        if ihsg_trend == "Bearish Kuat":
            result["notes"] = "IHSG sedang Bearish Kuat -- pertimbangkan ekstra hati-hati / size lebih kecil untuk sinyal Buy manapun."
        return result

    if support_level and current_price is not None and current_price >= support_level:
        gap_pct = (current_price - support_level) / support_level
        if gap_pct <= PROXIMITY_THRESHOLD_PCT / 100:
            result = {
                "recommendation": "Buy",
                "recommendation_price_low": round_to_tick(support_level),
                "recommendation_price_high": round_to_tick(support_level * 1.01),
            }
            if support_level_3:
                result["support_reference_extended"] = round_to_tick(support_level_3)
            if support_level_2:
                risk_per_share = current_price - support_level_2
                if risk_per_share > 0:
                    result["stop_loss"] = round_to_tick(support_level_2)
                    from fd_trade.utils.risk_engine import calculate_position_sizing
                    sizing = calculate_position_sizing(ticker, current_price, risk_per_share)
                    if sizing:
                        result["risk_amount"] = sizing["risk_amount"]
                        result["risk_per_share"] = sizing["risk_per_share"]
                        result["suggested_lot"] = sizing["final_lot"]
                        result["suggested_position_rp"] = sizing["suggested_position_rp"]
                        result["sizing_limiting_factor"] = sizing["limiting_factor"]
            notes = []
            if ihsg_trend == "Bearish Kuat":
                notes.append("IHSG sedang Bearish Kuat -- pertimbangkan ekstra hati-hati / size lebih kecil untuk sinyal Buy manapun.")
            elif ihsg_trend in ("Bullish Kuat", "Bullish Lemah"):
                notes.append("Selaras dengan trend IHSG.")
            if volume_status == "Volume Rendah":
                notes.append("Volume Rendah: sinyal Buy dekat support perlu dikonfirmasi lebih hati-hati.")
            if proximity:
                result["proximity"] = proximity
            if notes:
                result["notes"] = " ".join(notes)
            return result

    if (resistance_level and current_price is not None and current_price <= resistance_level
            and trend != "Bullish Kuat"):
        gap_pct = (resistance_level - current_price) / resistance_level
        if gap_pct <= PROXIMITY_THRESHOLD_PCT / 100:
            result = {
                "recommendation": "Sell",
                "recommendation_price_low": round_to_tick(resistance_level * 0.99),
                "recommendation_price_high": round_to_tick(resistance_level),
            }
            if resistance_level_2:
                result["take_profit_next"] = round_to_tick(resistance_level_2)
            if resistance_level_3:
                result["take_profit_extended"] = round_to_tick(resistance_level_3)
            if proximity:
                result["proximity"] = proximity
            return result

    result = {"recommendation": "Wait"}
    if proximity:
        result["proximity"] = proximity
    return result


def get_pivot_points(ticker, period="daily"):
    """Hitung Pivot Point classic (S1-S3, R1-R3) dari data OHLC yfinance.
    period: 'daily' (pakai H/L/C candle sebelumnya, sudah closed) atau 'weekly'.

    Fail-silent: return None kalau data tidak tersedia, konsisten dengan
    pola get_support_resistance() yang sudah ada di file ini.

    CATATAN: ini metode terpisah dari get_support_resistance() (swing+MA).
    Keduanya sengaja tidak digabung jadi satu angka -- dipakai berdampingan
    lewat check_confluence() supaya transparan kapan keduanya sepakat
    (confluence) vs kapan berbeda (perlu kehati-hatian ekstra).
    """
    import yfinance as yf
    import frappe

    yf_ticker = ticker if ticker.startswith("^") else f"{ticker}.JK"
    interval = "1d" if period == "daily" else "1wk"

    try:
        data = yf.Ticker(yf_ticker).history(period="1mo", interval=interval)
        if data is None or len(data) < 2:
            return None

        prev = data.iloc[-2]
        H, L, C = prev["High"], prev["Low"], prev["Close"]
        PP = (H + L + C) / 3

        R1 = (2 * PP) - L
        S1 = (2 * PP) - H
        R2 = PP + (H - L)
        S2 = PP - (H - L)
        R3 = H + 2 * (PP - L)
        S3 = L - 2 * (H - PP)

        return {
            "pivot": round(PP, 2),
            "S1": round(S1, 2), "S2": round(S2, 2), "S3": round(S3, 2),
            "R1": round(R1, 2), "R2": round(R2, 2), "R3": round(R3, 2),
            "period": period,
        }
    except Exception as e:
        frappe.log_error(f"get_pivot_points failed for {ticker}: {e}", "FD-Trade Pivot Points")
        return None


def check_confluence(swing_ma_level, pivot_level, threshold_pct=2.0):
    """Cek apakah level swing+MA dan pivot point saling berdekatan (confluence).
    Confluence = dua metode independen sepakat -> level lebih kredibel.
    Divergen = wajar terjadi karena horizon waktu beda (pivot jangka pendek
    vs swing 6 bulan) -- BUKAN berarti salah satu keliru.

    Return: (is_confluent: bool, delta_pct: float atau None kalau data kosong)
    """
    if not swing_ma_level or not pivot_level:
        return False, None
    delta_pct = abs(swing_ma_level - pivot_level) / swing_ma_level * 100
    return delta_pct <= threshold_pct, round(delta_pct, 2)
