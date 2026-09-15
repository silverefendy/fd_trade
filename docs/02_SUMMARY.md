# FD-Trade — Ringkasan Teknis

## 1. Identitas Aplikasi
- **Nama app**: `fd_trade`
- **Module**: FD-Trade
- **Author**: Efendy (silverefendy)
- **Lisensi**: MIT
- **Target**: Site Frappe baru & terpisah, khusus trading IDX pribadi (bukan multi-tenant, bukan produk komersial)

## 2. Struktur DocType

| DocType | Tipe | Fungsi |
|---|---|---|
| **Trading Account Settings** | Single | Konstanta akun (modal, limit risiko) + kredensial Telegram |
| **Trade Journal** | Normal, autoname `TRX-{YY}{MM}-{####}` | Inti sistem: entry, risk calc, exit, psikologi |
| **Signal Source** | Normal | Layar screening tip informal sebelum jadi entry |
| **Watchlist** | Normal | Kandidat saham + S/R otomatis |
| **Broker Summary** | Normal | Data bandarmologi harian per ticker (import Excel) |
| **Broker Summary Detail** | Child table | Baris detail broker (buy/sell side) dari Broker Summary |
| **Price Alert** | Normal | Alert harga terikat ke satu Trade Journal, dicek scheduler |

## 3. Alur Data Utama

```
Signal Source (screening) ──▶ Watchlist (S/R otomatis via yfinance)
                                     │
                                     ▼
                            Trade Journal (entry)
                        ┌────────────┼─────────────┐
                        ▼            ▼              ▼
                 Risk validation  Target price   Price Alert
                 (4 guard rails)  otomatis (R-    (dicek tiap
                 saat is_new()    multiple)       15 menit)
                        │
                        ▼
                  Trade Journal (exit, Closed)
                        │
                        ▼
              Telegram notification (notify_on_close)

Broker Summary (import Excel) ──▶ insight_notes otomatis
```

## 4. Modul Utility

- `fd_trade/utils/telegram.py` — satu fungsi `send_telegram_notification()`, dipakai semua notifikasi. Gagal silent (log error, tidak raise) — desain yang tepat untuk fungsi non-kritikal seperti ini.
- `fd_trade/utils/price_data.py` — dua fungsi:
  - `get_current_price(ticker)` — harga terakhir via yfinance (`.JK` suffix otomatis)
  - `get_support_resistance(ticker)` — swing high/low (window 5 hari) + MA20/50/200 dari histori 6 bulan
- `fd_trade/tasks.py` — 5 fungsi scheduled job, semua wrapped try/except + `frappe.log_error`, konsisten.

## 5. Scheduler (hooks.py)
```
*/30 9-16 * * 1-5  → check_intraday_conditions
*/15 9-16 * * 1-5  → check_price_alerts
0 16 * * 1-5       → daily_review_notification
0 17 * * 5         → weekly_review_notification
0 8 1 * *          → monthly_circuit_breaker_check
```
Ditambah `doc_events`: `Trade Journal.on_update → notify_on_close` (perhatikan potensi duplikasi — lihat 03_BUGS.md poin #1).

## 6. Observasi Arsitektur (bukan bug, tapi worth catatan)

1. **Dua versi query yang berbeda beredar untuk fungsi yang sama.** Skrip `setup_price_alert.sh` menulis ulang `trade_journal.py` memakai `frappe.db.get_list()` dengan agregasi `SUM(...)` sebagai nama field — pola ini **tidak selalu didukung** oleh query builder Frappe versi tertentu (`get_list` mengharapkan nama kolom asli, bukan ekspresi agregat, kecuali versi Frappe yang mendukung raw SQL expression di `fields`). Versi terbaru di repo sudah beralih ke `frappe.db.sql()` langsung — ini lebih aman dan eksplisit. **Kesimpulan: versi terbaru sudah benar, tapi kalau `setup_price_alert.sh` dijalankan ulang di masa depan, dia akan menimpa balik ke versi lama yang berisiko.** Sebaiknya script installer sekali-pakai ini dihapus/diarsipkan setelah dipakai, jangan disimpan sebagai bagian permanen dari repo.

2. **Single source of truth untuk skema DocType ganda.** `trade_journal.json` versi terbaru (dengan `sr_section`) berbeda dari versi yang ditulis ulang oleh `setup_price_alert.sh` (tanpa `sr_section`). Kalau script bash itu dijalankan lagi, field Support/Resistance akan **hilang** dari Trade Journal karena tertimpa. Ini bahaya nyata untuk data hilang.

3. Tidak ada folder `fd_trade/fd_trade/api/` yang berisi endpoint whitelisted terpisah — semua `@frappe.whitelist()` menempel langsung di controller doctype masing-masing (`fetch_support_resistance`, `import_from_excel`). Ini pola yang sah di Frappe, tapi kalau aplikasi berkembang, pertimbangkan pindahkan whitelisted function ke `api/` supaya lebih mudah di-maintain terpisah dari lifecycle hooks.

4. `Trading Account Settings` adalah Single DocType tanpa `on_update` yang menyiarkan ulang cache — kalau field `modal_total` diubah di tengah hari trading, semua kalkulasi berikutnya otomatis pakai nilai baru (karena selalu `frappe.get_single()` fresh tiap validate) — ini sudah benar, tidak perlu cache invalidation tambahan.

## 7. Dependency Eksternal & Risiko
- **yfinance**: gratis tapi tidak resmi didukung untuk data historis IDX secara stabil jangka panjang — Yahoo Finance beberapa kali mengubah struktur data tanpa pemberitahuan. Risiko: `get_current_price`/`get_support_resistance` bisa berhenti bekerja sewaktu-waktu tanpa perubahan kode di sisi Anda.
- **Tidak ada rate-limiting/backoff** pada pemanggilan yfinance di `check_price_alerts` — kalau jumlah alert aktif banyak, loop memanggil yfinance satu-per-satu tiap 15 menit bisa kena throttle/block dari Yahoo.
