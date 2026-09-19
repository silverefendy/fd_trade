# FD-Trade — Ringkasan Teknis

> Terakhir ditulis ulang: 19 September 2026. Menggantikan versi sebelumnya yang belum mencakup Watchlist Signal, risk_engine, IHSG regime, Price History, Pattern Detection, dan Chart Candlestick.

## 1. Identitas Aplikasi
- **Nama app**: `fd_trade`
- **Module**: FD-Trade
- **Author**: Efendy (silverefendy)
- **Lisensi**: MIT
- **Target**: Site Frappe baru & terpisah, khusus trading IDX pribadi (bukan multi-tenant, bukan produk komersial)

## 2. Struktur DocType (Terbaru)

| DocType | Tipe | Fungsi |
|---|---|---|
| **Trading Account Settings** | Single | Konstanta akun (modal, limit risiko) + kredensial Telegram + field IHSG regime (ihsg_current_price, ihsg_trend, ihsg_ma20, ihsg_ma50, ihsg_last_updated) |
| **Trade Journal** | Normal, autoname `TRX-{YY}{MM}-{####}` | Inti sistem: entry, risk calc (via risk_engine.py), exit, psikologi |
| **Signal Source** | Normal | Layar screening tip informal sebelum jadi entry |
| **Watchlist** | Normal | Kandidat saham + S/R 3-level otomatis + trend_status + trigger Price History/Watchlist Signal |
| **Watchlist Signal** | Normal | Histori rekomendasi Buy/Sell/Wait/Avoid per-refresh, termasuk stop_loss, linked_trade, detected_patterns (JSON), pattern_summary |
| **IHSG Signal** | Normal | Histori market regime IHSG (Risk-On/Neutral/Risk-Off/Avoid New Entry) — hanya informasi, tidak mengubah rekomendasi saham individual secara otomatis |
| **Price History** | Normal | Data OHLCV historis per ticker/timeframe, unique index (ticker+date+timeframe) — fondasi chart & pattern detection |
| **Broker Summary** | Normal | Data bandarmologi harian per ticker (import Excel) |
| **Broker Summary Detail** | Child table | Baris detail broker (buy/sell side) dari Broker Summary |
| **Price Alert** | Normal | Alert harga terikat ke satu Trade Journal, dicek scheduler |

## 3. Alur Data Utama (Terbaru)

Signal Source (screening)
│
▼
Watchlist (S/R 3-level otomatis via yfinance, trend_status, track_price_history)
│
├──▶ Price History (backfill + refresh harian 16:30 WIB)
│ │
│ ▼
│ Pattern Detection (6 pola: Double Top/Bottom,
│ H&S/Inverse H&S, Cup&Handle/Inverted)
│ │
│ ▼
└──▶ Watchlist Signal (Buy/Sell/Wait/Avoid + stop_loss +
detected_patterns + pattern_summary, via risk_engine.py
+ get_open_exposure() dari Trade Journal aktif)
│
▼
Chart Candlestick (Lightweight Charts) + overlay pola
│
▼
Trade Journal (entry, kalau jadi dieksekusi)
┌────────────┼─────────────┐
▼ ▼ ▼
Risk validation Target price Price Alert
(4 guard rails) otomatis (R- (dicek tiap
saat is_new() multiple) 15 menit)
│
▼
Trade Journal (exit, Closed)
│
▼
Telegram notification (notify_on_close)

IHSG (^JKSE) ──▶ refresh_ihsg_trend() ──▶ Trading Account Settings
(ihsg_trend) + histori IHSG Signal
(konteks regime, tidak mengubah
rekomendasi saham otomatis)

Broker Summary (import Excel) ──▶ insight_notes otomatis


## 4. Modul Utility

- `fd_trade/utils/telegram.py` — satu fungsi `send_telegram_notification()`, dipakai semua notifikasi. Fail-silent (log error, tidak raise).
- `fd_trade/utils/price_data.py`:
  - `get_current_price(ticker)` — harga terakhir via yfinance (`.JK` suffix otomatis, kecuali ticker index berawalan `^`)
  - `get_current_ohlc(ticker)` — OHLC harian terakhir
  - `get_support_resistance(ticker)` — S1-S3/R1-R3 dari swing high/low + MA20/50/200, proximity default 3%, validasi volume 20 hari (threshold tinggi >1,5x rata-rata, rendah <0,5x), plus trend_status (5 kategori berbasis gap% MA20 vs MA50)
  - `calculate_recommendation(...)` — logic rekomendasi Buy/Sell/Wait/Avoid, termasuk `stop_loss` (dari support_level_2) dan `sizing_limiting_factor`
- `fd_trade/utils/risk_engine.py` — perhitungan position sizing terpusat (`calculate_position_sizing()`), `get_open_exposure()` untuk baca sisa dana dari Trade Journal aktif
- `fd_trade/utils/pattern_detection.py` — `detect_chart_patterns(ohlc_data, lookback_days=90)`, 6 pola chart (Double Bottom/Top, Inverse H&S/H&S, Cup and Handle/Inverted — confidence maksimal "tentative" untuk 2 yang terakhir karena lebih rawan false-positive)
- `fd_trade/public/js/price_history_chart.js` — render chart candlestick (Lightweight Charts via CDN unpkg.com, lazy-load), toggle Daily/Hourly (Hourly masih "segera hadir")
- `fd_trade/tasks.py` — scheduled jobs, semua wrapped try/except + `frappe.log_error`:
  - `check_intraday_conditions`, `check_price_alerts`, `daily_review_notification`, `weekly_review_notification`, `monthly_circuit_breaker_check` (lama)
  - `refresh_all_watchlist()` + wrapper whitelisted `refresh_all_watchlist_now()`
  - `refresh_open_trades_sr()`
  - `refresh_ihsg_trend()` + wrapper whitelisted `refresh_ihsg_trend_now()`
  - `backfill_price_history()`, `refresh_price_history_daily()`, `cleanup_old_price_history()` (retensi 365 hari)

## 5. Scheduler (hooks.py)

1-59/15 9-16 * * 1-5 → check_price_alerts
*/30 9-16 * * 1-5 → check_intraday_conditions
2-59/30 9-16 * * 1-5 → refresh_open_trades_sr
3-59/30 9-16 * * 1-5 → refresh_ihsg_trend
0 16 * * 1-5 → daily_review_notification
0 17 * * 5 → weekly_review_notification
0 8 1 * * → monthly_circuit_breaker_check
30 16 * * 1-5 → refresh_price_history_daily
0 18 * * 5 → cleanup_old_price_history

Ditambah `doc_events`: `Trade Journal.on_update → notify_on_close` (potensi duplikasi — lihat BUG #1 di `03_BUGS.md`), dan `Watchlist.on_update → create_signal` via flag `_pending_signal_refresh` (fix BUG #9, dipindah dari `before_save()` untuk hindari race condition insert).

`add_to_apps_screen` **belum ditambahkan** ke hooks.py — tile "FD-Trade" di Apps Screen Frappe v16 masih belum muncul (lihat catatan di 05_SESSION_LOG.md).

## 6. Observasi Arsitektur

1. **`setup_price_alert.sh` masih berisiko** — script installer lama menimpa ulang `trade_journal.json` ke versi tanpa field S/R terbaru kalau dijalankan lagi. Sebaiknya dihapus/diarsipkan dari root repo (lihat BUG #5).
2. **Race condition lifecycle Frappe** — pelajaran dari BUG #9: untuk dokumen BARU, `before_save()` jalan SEBELUM baris ter-INSERT ke DB, jadi operasi yang butuh Link field valid ke dokumen itu sendiri (misal membuat child doctype terkait) harus dipindah ke `on_update()`, bukan `before_save()`.
3. Tidak ada folder `fd_trade/fd_trade/api/` terpisah — semua `@frappe.whitelist()` menempel langsung di controller doctype masing-masing. Sah untuk skala aplikasi ini, tapi pertimbangkan dipindah kalau makin berkembang.
4. `Trading Account Settings` (Single) selalu baca fresh via `frappe.get_single()` tiap validate — tidak perlu cache invalidation tambahan.

## 7. Dependency Eksternal & Risiko
- **yfinance**: gratis tapi tidak resmi didukung untuk data IDX jangka panjang — bisa berhenti bekerja sewaktu-waktu tanpa perubahan kode di sisi kita. Delay data 15-20 menit, selalu perlu konfirmasi manual sebelum eksekusi real.
- **Tidak ada rate-limiting/backoff** pada pemanggilan yfinance di loop (`check_price_alerts`, `refresh_all_watchlist`, backfill Price History) — risiko throttle/block dari Yahoo kalau jumlah ticker/alert aktif banyak.
- **Lightweight Charts via CDN unpkg.com** — dependency eksternal baru untuk fitur chart; kalau CDN tidak bisa diakses (jaringan berbeda dari kantor), chart akan gagal total. Belum ada fallback/self-hosted bundle.
- Update S/R (18 Sep 2026): S1-S3/R1-R3 dari swing high/low + MA20/50/200, proximity 3%, validasi volume 20 hari. Sumber harga otomatis tetap yfinance; tidak ada scraping broker, Stockbit, atau IDX.
- IHSG regime (Risk-On/Neutral/Risk-Off/Avoid New Entry) hanya konteks informasi, **tidak** mengubah rekomendasi saham individual secara otomatis (perlu keputusan desain lanjutan kalau mau diaktifkan sebagai risk multiplier — lihat riset backtest v11.x yang belum tuntas).
