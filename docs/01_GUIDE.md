# FD-Trade — Panduan Instalasi & Penggunaan

## 1. Apa itu FD-Trade?

FD-Trade adalah aplikasi Frappe custom untuk **jurnal trading pribadi** saham IDX (Bursa Efek Indonesia), dengan fokus pada:
- Manajemen risiko yang dipaksakan lewat validasi sistem (bukan sekadar niat baik)
- Pencatatan psikologi trading (FOMO, revenge trading, emosi)
- Screening sinyal informal (grup Telegram/Discord) sebelum dieksekusi
- Analisis broker flow ("bandarmologi") dari data Stockbit
- Notifikasi Telegram otomatis

Ini BUKAN sistem eksekusi order — murni jurnal + validasi + notifikasi. Filosofi ini bagus: memisahkan "sistem yang menegakkan disiplin" dari "eksekusi manual", karena trader (siapapun) paling sering gagal bukan karena analisis, tapi karena tidak patuh pada rencana sendiri.

## 2. Instalasi

### Prasyarat
- Frappe Framework (bench) sudah terpasang
- Python 3.8+
- MariaDB/MySQL
- Situs Frappe **baru dan terpisah** — jangan pasang di site ERPNext yang sudah dipakai produksi lain

### Langkah instalasi
```bash
bench get-app https://github.com/silverefendy/fd_trade
bench install-app fd_trade
bench build
bench restart
```

### Dependency
- `requests` — untuk Telegram Bot API
- `openpyxl` — parsing Excel broker summary
- `yfinance` — harga saham (delay 15-20 menit, best-effort, gratis)

## 3. Setup Awal (WAJIB sebelum pakai)

1. **Trading Account Settings** (Single DocType) — isi dulu sebelum membuat Trade Journal apapun:
   - Modal Total
   - Risk Per Trade Percent (default 0.5%)
   - Risk Per Trade Fast Percent (0.25%) — field ini ada tapi **belum dipakai di kode manapun**, lihat 03_BUGS.md
   - Daily/Weekly/Monthly Loss Limit
   - Max Exposure, Max Per Stock, Max Sektor (Max Sektor juga belum dipakai — lihat 03_BUGS.md)
   - Max Consecutive Losses

   ⚠️ Kalau dokumen ini belum pernah disimpan sekali saja, `calculate_risk_metrics()` di Trade Journal akan **crash** saat validate() karena `frappe.get_single()` akan gagal ambil default value yang benar. Selalu buka & Save dokumen ini dulu setelah instalasi.

2. **Setup Bot Telegram**:
   - Buat bot via `@BotFather` di Telegram → dapat token
   - Dapatkan chat ID via `@userinfobot`
   - Masuk ke Trading Account Settings → isi Bot Token (field Password, otomatis ter-mask) dan Chat ID
   - Centang "Telegram Notifications Enabled"

## 4. Alur Kerja Harian

### A. Sebelum entry (screening sinyal, opsional)
Kalau dapat tip dari grup Telegram/Discord → catat dulu di **Signal Source**, isi status New → Screening → baru putuskan Rejected atau Promoted to Watchlist. Jangan langsung entry dari tip mentah.

### B. Watchlist
Tambahkan ticker kandidat, isi tier (A/B/C), sektor, checklist kriteria. Klik tombol **"Fetch Support/Resistance"** untuk ambil level S/R otomatis dari yfinance (kombinasi swing high/low 6 bulan + MA20/50/200).

### C. Entry — Trade Journal
1. Isi Date, Ticker, Setup (Breakout/Pullback/Other), Market Regime
2. Isi Entry Price & Stop Loss → sistem otomatis hitung:
   - Risk Amount (berdasar % risiko dari modal)
   - Suggested Lot (dibulatkan ke bawah kelipatan 100 lembar)
   - Target Suggestions (3 skenario: Conservative 1.5R / Moderate 2.5R / Aggressive 4R)
   - Target Price otomatis mengikuti Target Category yang dipilih (pilih "Custom" untuk isi manual)
3. Sistem menjalankan validasi risiko **hanya saat dokumen baru dibuat** (bukan saat update):
   - Daily loss limit
   - Consecutive losses
   - Per-stock exposure
   - Total portfolio exposure
   Kalau melanggar → `frappe.throw()`, dokumen tidak bisa disimpan.
4. Opsional: klik **"Fetch Support/Resistance"** juga tersedia di Trade Journal.

### D. Price Alert
Buat alert baru, link ke Trade Journal terkait, isi trigger price & kondisi (>=/<=). Scheduler cek tiap 15 menit selama jam bursa (09:00–16:00, Senin–Jumat) via yfinance, kirim notifikasi Telegram kalau kena, lalu status berubah jadi "Triggered" otomatis.

### E. Exit
Isi Exit Price, ubah Status ke "Closed" → `result_rp` terhitung otomatis (butuh `position_lot` terisi), dan notifikasi Telegram "Trade Closed" terkirim otomatis (lihat catatan dobel-notifikasi di 03_BUGS.md).

### F. Psikologi (wajib diisi jujur)
Followed System, FOMO, Revenge, Emotion, Mistake, Lesson — ini bagian yang paling sering diabaikan trader tapi justru paling penting untuk membangun disiplin jangka panjang.

### G. Broker Summary (bandarmologi)
1. Copy tabel broker summary dari Stockbit web
2. Paste ke Excel, simpan
3. Attach file Excel di Broker Summary → klik "Import from Excel"
4. Sistem baca posisi cell tetap (fixed cell position — lihat 03_BUGS.md soal kerapuhan pendekatan ini)
5. Insight notes ter-generate otomatis (distribusi/akumulasi besar)

## 5. Notifikasi Terjadwal (otomatis)
| Job | Jadwal |
|---|---|
| Cek kondisi intraday | Tiap 30 menit, jam bursa |
| Cek Price Alert | Tiap 15 menit, jam bursa |
| Review harian | 16:00, Senin-Jumat |
| Review mingguan | Jumat 17:00 |
| Circuit breaker bulanan | Tanggal 1, jam 08:00 |

## 6. Yang Perlu Diperhatikan Sebelum Pakai Serius
- Baca **03_BUGS.md** dulu — ada bug notifikasi dobel dan satu potensi crash yang sebaiknya diperbaiki sebelum dipakai untuk uang sungguhan.
- Data yfinance delay 15-20 menit — jangan jadikan acuan eksekusi real-time, selalu konfirmasi manual di aplikasi broker sebelum eksekusi (sudah diingatkan di pesan alert, bagus).
- Ini sistem *disiplin*, bukan sistem *prediksi*. Target price berbasis R-multiple adalah kerangka matematis, bukan jaminan harga akan sampai ke sana — kode sudah benar mengingatkan ini di komentar, pertahankan mindset itu saat pakai.
