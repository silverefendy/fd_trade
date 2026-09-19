"""Deteksi pola chart berbasis swing point dari data Price History."""


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
        if all(value is not None for value in highs) and high == max(highs):
            peaks.append((index, high, "peak"))
        if all(value is not None for value in lows) and low == min(lows):
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
    for left, right in zip(points, points[1:]):
        if right[0] <= left[0]:
            continue
        between = [item for item in opposite if left[0] < item[0] < right[0]]
        if not between or not _similar(left[1], right[1], 0.03):
            continue
        neckline = max(item[1] for item in between) if bullish else min(item[1] for item in between)
        close = _safe_float(data[-1].get("close"))
        confirmed = close is not None and ((close >= neckline if bullish else close <= neckline))
        key_points = [_point(data, left[0], left[1], left[2]), _point(data, between[0][0], neckline, "neckline"), _point(data, right[0], right[1], right[2])]
        return {
            "pattern_name": name, "direction": direction, "confidence_level": "confirmed",
            "key_points": key_points, "neckline_price": float(neckline),
            "status": "confirmed" if confirmed else "forming",
            "notes": f"Dua {'lembah' if bullish else 'puncak'} mirip terdeteksi; neckline {'sudah ditembus' if confirmed else 'belum dikonfirmasi'}.",
        }
    return None


def _shoulder_pattern(data, peaks, troughs, bullish):
    points = troughs if bullish else peaks
    opposite = peaks if bullish else troughs
    name = "Inverse Head and Shoulders" if bullish else "Head and Shoulders"
    direction = "Bullish" if bullish else "Bearish"
    for left, head, right in zip(points, points[1:], points[2:]):
        shoulders_similar = _similar(left[1], right[1], 0.05)
        head_valid = head[1] < left[1] and head[1] < right[1] if bullish else head[1] > left[1] and head[1] > right[1]
        between = [item for item in opposite if left[0] < item[0] < right[0]]
        if not shoulders_similar or not head_valid or len(between) < 2:
            continue
        neckline = (between[0][1] + between[-1][1]) / 2
        close = _safe_float(data[-1].get("close"))
        confirmed = close is not None and ((close >= neckline if bullish else close <= neckline))
        return {
            "pattern_name": name, "direction": direction, "confidence_level": "confirmed",
            "key_points": [_point(data, left[0], left[1], left[2]), _point(data, head[0], head[1], head[2]), _point(data, right[0], right[1], right[2]), _point(data, between[0][0], neckline, "neckline"), _point(data, between[-1][0], neckline, "neckline")],
            "neckline_price": float(neckline), "status": "confirmed" if confirmed else "forming",
            "notes": f"Tiga {'lembah' if bullish else 'puncak'} berurutan dengan kepala yang {'lebih dalam' if bullish else 'lebih tinggi'}.",
        }
    return None


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
    return results
