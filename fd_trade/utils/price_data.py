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


def get_daily_ohlc_history(ticker, period="1y"):
    """Ambil histori OHLCV harian dari yfinance secara fail-silent."""
    try:
        full_ticker = ticker if ticker.startswith("^") else f"{ticker}.JK"
        history = yf.Ticker(full_ticker).history(period=period)
        if history is None or history.empty:
            frappe.log_error(f"No history found for ticker {full_ticker}", "FD-Trade Price History")
            return None

        rows = []
        for index, row in history.iterrows():
            trading_date = index.date().isoformat() if hasattr(index, "date") else str(index)[:10]
            rows.append({
                "date": trading_date,
                "open": round_to_tick(float(row["Open"])),
                "high": round_to_tick(float(row["High"])),
                "low": round_to_tick(float(row["Low"])),
                "close": round_to_tick(float(row["Close"])),
                "volume": float(row["Volume"]) if row["Volume"] is not None else 0,
            })
        return rows or None
    except Exception as e:
        frappe.log_error(f"get_daily_ohlc_history failed for {ticker}: {e}", "FD-Trade Price History")
        return None

def get_support_resistance(ticker):
    """Hitung 3 level support & resistance dari Volume Profile (POC + HVN),
    plus trend classification dari MA20/50/200 -- semua dari data Price
    History yang sudah tersimpan (bukan fetch live yfinance lagi, per
    keputusan 20 Sep 2026: satu sumber kebenaran OHLCV, Opsi A).

    Kalau data Price History belum cukup (ticker baru ditambahkan,
    backfill belum jalan), fallback ke backfill on-the-spot sekali,
    lalu coba lagi.
    """
    from fd_trade.utils.volume_profile import get_price_history_rows, calculate_volume_profile

    try:
        rows = get_price_history_rows(ticker, lookback_days=250)

        if len(rows) < 30:
            _backfill_cold_start(ticker)
            rows = get_price_history_rows(ticker, lookback_days=250)

        if len(rows) < 30:
            frappe.log_error(f"Data Price History tidak cukup utk {ticker} (bahkan setelah backfill)", "FD-Trade Price Data")
            return None

        closes = [r["close"] for r in rows if r.get("close")]
        current_price = closes[-1]

        def sma(values, period):
            if len(values) < period:
                return None
            return sum(values[-period:]) / period

        ma20 = sma(closes, 20)
        ma50 = sma(closes, 50)
        ma200 = sma(closes, 200)

        vp = calculate_volume_profile(ticker, current_price=current_price, rows=rows)
        if not vp:
            return None

        detail_lines = [f"Current Price: Rp{current_price:,.0f}", f"POC (Point of Control): Rp{vp['poc']:,.0f}"]
        detail_lines.append(f"Value Area: Rp{vp['value_area_low']:,.0f} - Rp{vp['value_area_high']:,.0f}")
        if ma20:
            detail_lines.append(f"MA20: Rp{ma20:,.0f}")
        if ma50:
            detail_lines.append(f"MA50: Rp{ma50:,.0f}")
        if ma200:
            detail_lines.append(f"MA200: Rp{ma200:,.0f}")

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

        levels = _complete_sr_levels(vp, rows, current_price, [ma20, ma50, ma200])
        detail_lines.append(levels["note"])

        return {
            "support_level": levels["S"][0],
            "support_level_2": levels["S"][1],
            "support_level_3": levels["S"][2],
            "resistance_level": levels["R"][0],
            "resistance_level_2": levels["R"][1],
            "resistance_level_3": levels["R"][2],
            "poc": vp["poc"],
            "value_area_high": vp["value_area_high"],
            "value_area_low": vp["value_area_low"],
            "details": "\n".join(detail_lines),
            "trend": trend,
            "ma20": ma20,
            "ma50": ma50,
            "price_history_rows": rows,
        }

    except Exception as e:
        frappe.log_error(f"get_support_resistance failed for {ticker}: {e}", "FD-Trade Price Data")
        return None


# LEVEL-COMPLETE FIX (20 Sep 2026)
def _complete_sr_levels(vp, rows, current_price, mas):
    """Pastikan S1-S3 (menurun) & R1-R3 (menaik) SELALU terisi dan strict di sisi yang
    benar SETELAH pembulatan tick (dulu level bisa sama dengan harga). Volume Profile tetap
    jadi sumber utama; kekurangan diisi berurutan: Swing high/low -> MA -> proyeksi ATR14.
    Return {"S": [..3], "R": [..3], "note": "sumber tiap level"}; 0 = benar2 tidak ada."""
    price = float(current_price)
    highs = [float(r["high"]) for r in rows if r.get("high")]
    lows = [float(r["low"]) for r in rows if r.get("low")]

    w = 5
    hs, ls = highs[-125:], lows[-125:]
    swing_hi = [hs[i] for i in range(w, len(hs) - w) if hs[i] == max(hs[i - w:i + w + 1])]
    swing_lo = [ls[i] for i in range(w, len(ls) - w) if ls[i] == min(ls[i - w:i + w + 1])]

    trs = []
    for i in range(1, len(rows)):
        try:
            h, l, pc = float(rows[i]["high"]), float(rows[i]["low"]), float(rows[i - 1]["close"])
        except (TypeError, KeyError, ValueError):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = (sum(trs[-14:]) / len(trs[-14:])) if trs else 0
    if atr <= 0:
        atr = price * 0.03

    def build(side, primary, pools):
        out = []

        def ok(c):
            if not c or c <= 0:
                return False
            if side == "S":
                return c < price and (not out or c < out[-1][0] * 0.99)
            return c > price and (not out or c > out[-1][0] * 1.01)

        for lvl in primary:
            c = round_to_tick(lvl) if lvl else None
            if ok(c):
                out.append((c, "VP"))
        for name, cands in pools:
            for lvl in sorted(cands, reverse=(side == "S")):
                if len(out) == 3:
                    break
                c = round_to_tick(lvl)
                if ok(c):
                    out.append((c, name))
            if len(out) == 3:
                break
        step = 1.5
        while len(out) < 3 and step <= 20:
            ref = out[-1][0] if out else price
            c = round_to_tick(ref - atr * step if side == "S" else ref + atr * step)
            if side == "S" and (not c or c <= 0):
                break
            if ok(c):
                out.append((c, "ATR"))
            else:
                step += 0.5
        return out

    ma_vals = [m for m in mas if m]
    S = build("S", [vp.get(k) for k in ("support_level", "support_level_2", "support_level_3")],
              [("Swing", swing_lo), ("MA", ma_vals)])
    R = build("R", [vp.get(k) for k in ("resistance_level", "resistance_level_2", "resistance_level_3")],
              [("Swing", swing_hi), ("MA", ma_vals)])

    def lv(lst):
        return [x[0] for x in lst] + [0] * (3 - len(lst))

    def sr(lst):
        return [x[1] for x in lst] + ["-"] * (3 - len(lst))

    note = ("Sumber level: " + ", ".join(f"S{i + 1}={s}" for i, s in enumerate(sr(S)))
            + " | " + ", ".join(f"R{i + 1}={s}" for i, s in enumerate(sr(R))))
    return {"S": lv(S), "R": lv(R), "note": note}


def _backfill_cold_start(ticker):
    """Backfill Price History sekali untuk ticker yang datanya belum ada
    sama sekali, dipanggil dari get_support_resistance() saat cold-start."""
    from fd_trade.tasks import _store_price_history_for_ticker
    try:
        _store_price_history_for_ticker(ticker, period="1y")
    except Exception as e:
        frappe.log_error(f"Cold-start backfill gagal utk {ticker}: {e}", "FD-Trade Price History")


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


def get_volume_confirmation(ticker, price_history_rows=None, high_ratio=VOLUME_HIGH_RATIO,
                            low_ratio=VOLUME_LOW_RATIO):
    """Validasi volume terakhir terhadap rata-rata volume 20 hari, dari
    Price History (bukan yfinance live lagi, per keputusan 20 Sep 2026).

    ``price_history_rows`` opsional -- reuse dari get_support_resistance()
    supaya tidak query Price History dua kali untuk ticker yang sama.
    """
    try:
        if price_history_rows is None:
            from fd_trade.utils.volume_profile import get_price_history_rows
            price_history_rows = get_price_history_rows(ticker, lookback_days=30)

        volumes = [r["volume"] for r in price_history_rows if r.get("volume") is not None]
        if len(volumes) < VOLUME_AVERAGE_DAYS + 1:
            return None

        current_volume = float(volumes[-1])
        baseline_values = volumes[-(VOLUME_AVERAGE_DAYS + 1):-1]
        avg_volume = sum(baseline_values) / len(baseline_values)
        if avg_volume <= 0 or current_volume < 0:
            return None

        ratio = current_volume / avg_volume
        status = "Volume Tinggi" if ratio > high_ratio else "Volume Rendah" if ratio < low_ratio else "Volume Normal"

        return {"current_volume": current_volume, "avg_volume_20d": avg_volume, "volume_status": status}
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


def calculate_atr(rows, period=14):
    """Average True Range dari baris Price History (rows harus urut
    kronologis naik, field wajib: high, low, close). Formula sama persis
    dgn yang sudah dipakai internal di _complete_sr_levels() utk proyeksi
    level S/R fallback -- di-standalone-kan di sini (21 Sep 2026) supaya
    bisa dipakai jg sbg basis stop loss ATR (lihat calculate_recommendation).
    Return None (bukan estimasi price*0.03) kalau data tak cukup -- di
    titik pemakaian, None berarti "pakai fallback lain", bukan "pakai
    angka kira-kira"."""
    if not rows or len(rows) < 2:
        return None
    trs = []
    for i in range(1, len(rows)):
        try:
            h, l, pc = float(rows[i]["high"]), float(rows[i]["low"]), float(rows[i - 1]["close"])
        except (TypeError, KeyError, ValueError):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    # FIX (21 Sep 2026): wajib >= `period` sampel True Range supaya rata2
    # benar2 mewakili `period` hari, bukan rata2 dari segelintir sampel yg
    # tak reliabel (kasus nyata: saham baru listing/data historis pendek).
    # Ini titik yg membuat fallback ke support_level_2 di
    # calculate_recommendation() benar2 aktif saat dibutuhkan.
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / len(trs[-period:])


def calculate_recommendation(ticker, current_price, trend, support_level, support_level_2,
                              resistance_level, support_level_3=None,
                              resistance_level_2=None, resistance_level_3=None,
                              ihsg_trend=None, proximity=None, volume_status=None,
                              proximity_threshold_pct=None, price_history_rows=None):
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
    if proximity_threshold_pct is None:
        proximity_threshold_pct = PROXIMITY_THRESHOLD_PCT

    if trend == "Bearish Kuat":
        result = {"recommendation": "Avoid"}
        if ihsg_trend == "Bearish Kuat":
            result["notes"] = "IHSG sedang Bearish Kuat -- pertimbangkan ekstra hati-hati / size lebih kecil untuk sinyal Buy manapun."
        return result

    if support_level and current_price is not None and current_price >= support_level:
        gap_pct = (current_price - support_level) / support_level
        if gap_pct <= proximity_threshold_pct / 100:
            result = {
                "recommendation": "Buy",
                "recommendation_price_low": round_to_tick(support_level),
                "recommendation_price_high": round_to_tick(support_level * 1.01),
            }
            if support_level_3:
                result["support_reference_extended"] = round_to_tick(support_level_3)
            # STOP LOSS (21 Sep 2026): ATR sbg PRIMARY, support_level_2 fallback
            # murni teknis (dipakai HANYA kalau ATR tak bisa dihitung, misal
            # ticker baru listing/data historis <14 hari). Keputusan berdasar
            # riset backtest 750 hari x 22 ticker x 3 rezim IHSG: ATR-stop
            # (x1.5) mengalahkan S2-stop di SEMUA rezim, margin di atas
            # ambang 0.15R. Ini BUKAN hybrid "ambil yg lebih ketat" -- itu
            # sengaja ditolak krn ATR selalu lebih lebar dari S2 shg S2 akan
            # menang mayoritas kasus kalau dihibridkan.
            ATR_STOP_MULTIPLIER = 1.5
            atr14 = calculate_atr(price_history_rows) if price_history_rows else None
            stop_loss_price = None
            if atr14 and atr14 > 0:
                stop_loss_price = current_price - (atr14 * ATR_STOP_MULTIPLIER)
            if not stop_loss_price or stop_loss_price <= 0:
                stop_loss_price = support_level_2  # fallback teknis, bukan pengganti hasil riset

            if stop_loss_price:
                risk_per_share = current_price - stop_loss_price
                if risk_per_share > 0:
                    result["stop_loss"] = round_to_tick(stop_loss_price)
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
        if gap_pct <= proximity_threshold_pct / 100:
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


def calculate_market_regime(trend_status, current_price=None, ma20=None, ma50=None):
    """Klasifikasikan kondisi pasar IHSG tanpa mengubah rekomendasi saham.

    Risk-On memerlukan trend bullish dan harga di atas MA20 serta MA50.
    """
    if trend_status in ("Bullish Kuat", "Bullish Lemah"):
        if current_price is not None and ma20 is not None and ma50 is not None \
                and current_price > ma20 and current_price > ma50:
            return "Risk-On"
        return "Neutral"
    if trend_status == "Sideways":
        return "Neutral"
    if trend_status == "Bearish Lemah":
        return "Risk-Off"
    if trend_status == "Bearish Kuat":
        return "Avoid New Entry"
    return "Neutral"


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
