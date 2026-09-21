"""Backfill Price History 3 tahun (idempotent, aman diulang). Jalankan: %run /tmp/backfill_3y.py
Urutan: ^JKSE dulu (kalender bursa untuk filter baris hari libur), lalu semua saham."""
import time
import frappe
from fd_trade.tasks import _store_price_history_for_ticker

PERIOD = "3y"
tickers = ["^JKSE"] + frappe.db.sql_list(
    "select distinct ticker from `tabPrice History` where timeframe = 'Daily' and left(ticker, 1) <> '^' order by ticker")

t0 = time.time()
total = 0
for tk in tickers:
    t1 = time.time()
    try:
        n = _store_price_history_for_ticker(tk, period=PERIOD)
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        n = -1
        print("FAIL", tk, e)
    total += max(n, 0)
    print(f"{tk:7s} +{n:5d} baris ({time.time() - t1:.0f} dtk)", flush=True)
    time.sleep(1)
print(f"\nSELESAI: {total} baris baru, {time.time() - t0:.0f} dtk")
