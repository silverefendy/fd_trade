"""Deteksi pola chart berbasis swing point dari data Price History."""

MIN_DOUBLE_SEPARATION_DAYS = 15
MIN_SHOULDER_SEPARATION_DAYS = 10
MIN_PATTERN_DEPTH_PCT = 0.05
SIMILAR_DOUBLE_PCT = 0.03
SIMILAR_SHOULDER_PCT = 0.05


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _swing_points(data, window):
    peaks, troughs = [], []
    for index in range(window, len(data) - window):
        high = _safe_float(data[index].get("high"))
        low = _safe_float(data[index].get("low"))
        if high is None or low is None:
            continue
        highs = [_safe_float(row.get("high")) for row in data[index - window:index + window + 1]]
        lows = [_safe_float(row.get("low")) for row in data[index - window:index + window + 1]]
        if all(value is not None for value in highs) and high == max(highs) and highs.count(high) == 1:
            peaks.append((index, high, "peak"))
        if all(value is not None for value in lows) and low == min(lows) and lows.count(low) == 1:
            troughs.append((index, low, "trough"))
    return peaks, troughs


def _point(data, index, price, point_type):
    return {"date": str(data[index].get("date")), "price": float(price), "point_type": point_type}


def _similar(first, second, tolerance):
    return abs(first - second) / max(abs(first), 1e-9) <= tolerance


def _double_pattern(data, peaks, troughs, bullish):
    points = troughs if bullish else peaks
    opposite = peaks if bullish else troughs
    name = "Double Bottom" if bullish else "Double Top"
    direction = "Bullish" if bullish else "Bearish"
    candidates = []
    for left, right in zip(points, points[1:]):
        if right[0] - left[0] < MIN_DOUBLE_SEPARATION_DAYS:
            continue
        between = [item for item in opposite if left[0] < item[0] < right[0]]
        if not between or not _similar(left[1], right[1], SIMILAR_DOUBLE_PCT):
            continue
        neckline = max(item[1] for item in between) if bullish else min(item[1] for item in between)
        average_point = (left[1] + right[1]) / 2
        depth = abs(neckline - average_point) / max(abs(average_point), 1e-9)
        if depth < MIN_PATTERN_DEPTH_PCT:
            continue
        # BUG FIX (19 Sep 2026): (1) breakout wajib margin 1.5% dari neckline;
        # (2) confidence_level sebelumnya hardcode "confirmed" untuk semua
        # kandidat, tidak ikut status -- akar penyebab "Forming...confirmed".
        BREAKOUT_MARGIN_PCT = 0.015
        close = _safe_float(data[-1].get("close"))
        if close is not None and neckline:
            confirmed = (close >= neckline * (1 + BREAKOUT_MARGIN_PCT) if bullish
                         else close <= neckline * (1 - BREAKOUT_MARGIN_PCT))
        else:
            confirmed = False
        status = "confirmed" if confirmed else "forming"
        confidence_level = "confirmed" if confirmed else "tentative"
        key_points = [_point(data, left[0], left[1], left[2]), _point(data, between[0][0], neckline, "neckline"), _point(data, right[0], right[1], right[2])]
        candidates.append({
            "pattern_name": name, "direction": direction, "confidence_level": confidence_level,
            "key_points": key_points, "neckline_price": float(neckline),
            "status": status,
            "notes": f"Dua {'lembah' if bullish else 'puncak'} mirip terdeteksi; neckline {'sudah ditembus' if confirmed else 'belum dikonfirmasi'}.",
            "_amplitude": depth, "_latest_index": right[0],
        })
    return max(candidates, key=lambda item: (item["_amplitude"], item["_latest_index"])) if candidates else None


def _shoulder_pattern(data, peaks, troughs, bullish):
    points = troughs if bullish else peaks
    opposite = peaks if bullish else troughs
    name = "Inverse Head and Shoulders" if bullish else "Head and Shoulders"
    direction = "Bullish" if bullish else "Bearish"
    candidates = []
    for left, head, right in zip(points, points[1:], points[2:]):
        if head[0] - left[0] < MIN_SHOULDER_SEPARATION_DAYS or right[0] - head[0] < MIN_SHOULDER_SEPARATION_DAYS:
            continue
        shoulders_similar = _similar(left[1], right[1], SIMILAR_SHOULDER_PCT)
        head_valid = head[1] < left[1] and head[1] < right[1] if bullish else head[1] > left[1] and head[1] > right[1]
        between = [item for item in opposite if left[0] < item[0] < right[0]]
        if not shoulders_similar or not head_valid or len(between) < 2:
            continue
        neckline = (between[0][1] + between[-1][1]) / 2
        depth = abs(neckline - head[1]) / max(abs(head[1]), 1e-9)
        if depth < MIN_PATTERN_DEPTH_PCT:
            continue
        # BUG FIX (19 Sep 2026): fix sama seperti _double_pattern -- breakout
        # wajib margin 1.5% dari neckline, dan confidence_level (sebelumnya
        # hardcode "confirmed" untuk semua kandidat H&S/Inverse H&S) sekarang
        # ikut status aktual.
        BREAKOUT_MARGIN_PCT = 0.015
        close = _safe_float(data[-1].get("close"))
        if close is not None and neckline:
            confirmed = (close >= neckline * (1 + BREAKOUT_MARGIN_PCT) if bullish
                         else close <= neckline * (1 - BREAKOUT_MARGIN_PCT))
        else:
            confirmed = False
        status = "confirmed" if confirmed else "forming"
        confidence_level = "confirmed" if confirmed else "tentative"
        candidates.append({
            "pattern_name": name, "direction": direction, "confidence_level": confidence_level,
            "key_points": [_point(data, left[0], left[1], left[2]), _point(data, head[0], head[1], head[2]), _point(data, right[0], right[1], right[2]), _point(data, between[0][0], neckline, "neckline"), _point(data, between[-1][0], neckline, "neckline")],
            "neckline_price": float(neckline), "status": status,
            "notes": f"Tiga {'lembah' if bullish else 'puncak'} berurutan dengan kepala yang {'lebih dalam' if bullish else 'lebih tinggi'}.",
            "_amplitude": depth, "_latest_index": right[0],
        })
    return max(candidates, key=lambda item: (item["_amplitude"], item["_latest_index"])) if candidates else None


def _cup_pattern(data, bullish):
    name = "Cup and Handle" if bullish else "Inverted Cup and Handle"
    direction = "Bullish" if bullish else "Bearish"
    if len(data) < 30:
        return None
    cup_end = int(len(data) * 0.75)
    handle_start = cup_end
    cup = data[:cup_end]
    handle = data[handle_start:]
    start = _safe_float(cup[0].get("close"))
    end = _safe_float(cup[-1].get("close"))
    values = [_safe_float(row.get("close")) for row in cup]
    handle_values = [_safe_float(row.get("close")) for row in handle]
    if None in values or None in handle_values or not start or not end:
        return None
    extreme = min(values) if bullish else max(values)
    if abs(start - end) / start > 0.08:
        return None
    depth = (start - extreme) / start if bullish else (extreme - start) / start
    if depth < 0.08 or max(handle_values) - min(handle_values) > start * 0.08:
        return None
    breakout = handle_values[-1] >= max(start, end) * 1.01 if bullish else handle_values[-1] <= min(start, end) * 0.99
    volumes = [_safe_float(row.get("volume")) for row in data[-21:-1]]
    latest_volume = _safe_float(data[-1].get("volume"))
    high_volume = latest_volume is not None and volumes and latest_volume > sum(volumes) / len(volumes) * 1.5
    confidence = "confirmed" if breakout and high_volume else "tentative"
    return {
        "pattern_name": name, "direction": direction, "confidence_level": confidence,
        "key_points": [_point(data, 0, start, "peak" if not bullish else "peak"), _point(data, values.index(extreme), extreme, "peak" if not bullish else "trough"), _point(data, cup_end - 1, end, "peak" if not bullish else "peak")],
        "neckline_price": float(max(start, end) if bullish else min(start, end)),
        "status": "confirmed" if breakout else "forming",
        "notes": f"Pola {name} terdeteksi; confidence {confidence}.",
        "_amplitude": depth, "_latest_index": len(data) - 1,
    }


def detect_chart_patterns(ohlc_data, lookback_days=90):
    """Deteksi enam pola chart; kegagalan satu pola tidak menghentikan pola lain."""
    if not isinstance(ohlc_data, list) or not ohlc_data:
        return []
    data = ohlc_data[-lookback_days:]
    if len(data) < 7:
        return []
    window = 1 if len(data) < 20 else max(2, min(5, len(data) // 20))
    peaks, troughs = _swing_points(data, window)
    detectors = [
        lambda: _double_pattern(data, peaks, troughs, True),
        lambda: _double_pattern(data, peaks, troughs, False),
        lambda: _shoulder_pattern(data, peaks, troughs, True),
        lambda: _shoulder_pattern(data, peaks, troughs, False),
        lambda: _cup_pattern(data, True),
        lambda: _cup_pattern(data, False),
    ]
    results = []
    for detector in detectors:
        try:
            result = detector()
            if result:
                results.append(result)
        except Exception:
            continue
    # Satu snapshot tidak boleh menampilkan pola bullish dan bearish yang
    # sama-sama aktif. Pilih kandidat yang paling kuat, lalu paling baru.
    directions = {item["direction"] for item in results}
    if len(directions) > 1:
        results = [max(results, key=lambda item: (
            item.get("status") == "confirmed",
            item.get("_amplitude", 0),
            item.get("_latest_index", 0),
        ))]
    for item in results:
        item.pop("_amplitude", None)
        item.pop("_latest_index", None)
    return results
