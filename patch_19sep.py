import shutil
from pathlib import Path

BASE = Path("fd_trade")

def patch(path_str, edits):
    path = BASE / path_str
    backup = path.with_suffix(path.suffix + ".backup")
    shutil.copy(path, backup)
    content = path.read_text()
    for i, (old, new) in enumerate(edits, 1):
        assert old in content, f"[{path_str}] edit #{i}: old_str tidak ditemukan, cek manual!"
        assert content.count(old) == 1, f"[{path_str}] edit #{i}: old_str muncul lebih dari 1x, tidak aman diganti otomatis!"
        content = content.replace(old, new)
    path.write_text(content)
    print(f"OK  -> {path_str} (backup: {backup.name})")

# ---------- A1: price_data.py -- proximity_threshold_pct jadi parameter ----------
patch("utils/price_data.py", [
    (
        'def calculate_recommendation(ticker, current_price, trend, support_level, support_level_2,\n'
        '                              resistance_level, support_level_3=None,\n'
        '                              resistance_level_2=None, resistance_level_3=None,\n'
        '                              ihsg_trend=None, proximity=None, volume_status=None):',
        'def calculate_recommendation(ticker, current_price, trend, support_level, support_level_2,\n'
        '                              resistance_level, support_level_3=None,\n'
        '                              resistance_level_2=None, resistance_level_3=None,\n'
        '                              ihsg_trend=None, proximity=None, volume_status=None,\n'
        '                              proximity_threshold_pct=None):'
    ),
    (
        '    4. Selain itu -> Wait\n'
        '    """\n'
        '    if trend == "Bearish Kuat":',
        '    4. Selain itu -> Wait\n'
        '    """\n'
        '    if proximity_threshold_pct is None:\n'
        '        proximity_threshold_pct = PROXIMITY_THRESHOLD_PCT\n\n'
        '    if trend == "Bearish Kuat":'
    ),
    (
        '    if support_level and current_price is not None and current_price >= support_level:\n'
        '        gap_pct = (current_price - support_level) / support_level\n'
        '        if gap_pct <= PROXIMITY_THRESHOLD_PCT / 100:\n'
        '            result = {\n'
        '                "recommendation": "Buy",',
        '    if support_level and current_price is not None and current_price >= support_level:\n'
        '        gap_pct = (current_price - support_level) / support_level\n'
        '        if gap_pct <= proximity_threshold_pct / 100:\n'
        '            result = {\n'
        '                "recommendation": "Buy",'
    ),
    (
        '    if (resistance_level and current_price is not None and current_price <= resistance_level\n'
        '            and trend != "Bullish Kuat"):\n'
        '        gap_pct = (resistance_level - current_price) / resistance_level\n'
        '        if gap_pct <= PROXIMITY_THRESHOLD_PCT / 100:\n'
        '            result = {\n'
        '                "recommendation": "Sell",',
        '    if (resistance_level and current_price is not None and current_price <= resistance_level\n'
        '            and trend != "Bullish Kuat"):\n'
        '        gap_pct = (resistance_level - current_price) / resistance_level\n'
        '        if gap_pct <= proximity_threshold_pct / 100:\n'
        '            result = {\n'
        '                "recommendation": "Sell",'
    ),
])

# ---------- A2: watchlist_signal.py -- teruskan proximity_threshold ke calculate_recommendation ----------
patch("fd_trade/doctype/watchlist_signal/watchlist_signal.py", [
    (
        '            ihsg_trend=ihsg_trend,\n'
        '            proximity=proximity,\n'
        '            volume_status=volume.get("volume_status") if volume else None,\n'
        '        )',
        '            ihsg_trend=ihsg_trend,\n'
        '            proximity=proximity,\n'
        '            volume_status=volume.get("volume_status") if volume else None,\n'
        '            proximity_threshold_pct=proximity_threshold,\n'
        '        )'
    ),
])

# ---------- B: watchlist.py -- refresh_current_price ikut panggil create_signal ----------
patch("fd_trade/doctype/watchlist/watchlist.py", [
    (
        '    doc.last_updated = now()\n'
        '    doc.save()\n\n'
        '    return {"current_price": doc.current_price}',
        '    doc.last_updated = now()\n'
        '    doc.save()\n\n'
        '    from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import create_signal\n'
        '    create_signal(\n'
        '        watchlist_name=doc.name,\n'
        '        ticker=doc.ticker,\n'
        '        current_price=doc.current_price,\n'
        '        trend_status=doc.trend_status,\n'
        '        support_level=doc.support_level,\n'
        '        support_level_2=doc.support_level_2,\n'
        '        resistance_level=doc.resistance_level,\n'
        '        support_level_3=doc.support_level_3,\n'
        '        resistance_level_2=doc.resistance_level_2,\n'
        '        resistance_level_3=doc.resistance_level_3,\n'
        '    )\n\n'
        '    return {"current_price": doc.current_price}'
    ),
])

# ---------- C: trade_journal.py -- gabung 2 fix ----------
patch("fd_trade/doctype/trade_journal/trade_journal.py", [
    (
        '    def on_update(self):\n'
        '        """Trigger Telegram notification when trade is closed."""\n'
        '        if self.status == "Closed" and self.exit_price and self.result_r is not None:\n'
        '            notify_on_close(self)',
        '    def on_update(self):\n'
        '        """Trigger Telegram notification hanya saat transisi ke Closed,\n'
        '        bukan di setiap save berikutnya selama status masih Closed."""\n'
        '        if (self.status == "Closed" and self.exit_price and self.result_r is not None\n'
        '                and self.has_value_changed("status")):\n'
        '            notify_on_close(self)'
    ),
    (
        '        # Calculate result_rp if exit_price is set\n'
        '        if self.exit_price and self.position_lot:\n'
        '            self.result_rp = (self.exit_price - self.entry_price) * self.position_lot * 100',
        '        # Calculate result_rp if exit_price is set\n'
        '        if self.exit_price and self.position_lot:\n'
        '            self.result_rp = (self.exit_price - self.entry_price) * self.position_lot * 100\n\n'
        '        # Auto-hitung result_r dari R-multiple, tetap bisa di-override manual.\n'
        '        if self.exit_price and risk_per_share:\n'
        '            self.result_r = (self.exit_price - self.entry_price) / risk_per_share'
    ),
])

# ---------- D: broker_summary.py -- parse_excel_value tangani format negatif (1.5M) ----------
patch("fd_trade/doctype/broker_summary/broker_summary.py", [
    (
        '    # Remove commas\n'
        '    value_str = value_str.replace(",", "")\n\n'
        '    # Handle suffixes\n'
        '    if value_str.endswith("B"):\n'
        '        return float(value_str[:-1]) * 1000000000\n'
        '    elif value_str.endswith("M"):\n'
        '        return float(value_str[:-1]) * 1000000\n'
        '    elif value_str.endswith("K"):\n'
        '        return float(value_str[:-1]) * 1000\n'
        '    else:\n'
        '        try:\n'
        '            return float(value_str)\n'
        '        except ValueError:\n'
        '            return None',
        '    # Remove commas\n'
        '    value_str = value_str.replace(",", "")\n\n'
        '    # Format akuntansi negatif: (1.5M) -> -1.5M\n'
        '    is_negative = value_str.startswith("(") and value_str.endswith(")")\n'
        '    if is_negative:\n'
        '        value_str = value_str[1:-1]\n\n'
        '    # Handle suffixes\n'
        '    if value_str.endswith("B"):\n'
        '        result = float(value_str[:-1]) * 1000000000\n'
        '    elif value_str.endswith("M"):\n'
        '        result = float(value_str[:-1]) * 1000000\n'
        '    elif value_str.endswith("K"):\n'
        '        result = float(value_str[:-1]) * 1000\n'
        '    else:\n'
        '        try:\n'
        '            result = float(value_str)\n'
        '        except ValueError:\n'
        '            return None\n\n'
        '    return -result if is_negative else result'
    ),
])

print("\nSemua 4 file berhasil dipatch.")
