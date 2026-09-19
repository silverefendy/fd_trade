# FD-Trade — Daftar Fitur

> Terakhir ditulis ulang: 19 September 2026.

## 1. Fitur yang Sudah Ada & Berfungsi

### Manajemen Risiko
- ✅ Position sizing otomatis via `risk_engine.calculate_position_sizing()`, berdasar % risiko tetap dari modal
- ✅ Suggested lot otomatis (dibulatkan ke bawah kelipatan 100 lembar)
- ✅ Peringatan (bukan blokir) kalau posisi aktual melebihi 120% dari risiko yang disarankan
- ✅ Daily loss limit — blokir trade baru kalau limit harian terlampaui
- ✅ Consecutive loss circuit breaker — blokir trade baru setelah N kekalahan beruntun
- ✅ Per-stock exposure limit — blokir kalau eksposur ke satu ticker berlebihan
- ✅ Total portfolio exposure limit — otomatis memperhitungkan sisa dana dari Trade Journal aktif via `get_open_exposure()`, ikut mempengaruhi lot yang disarankan di Watchlist Signal tanpa logic tambahan
- ⚠️ Weekly loss limit — hanya kirim peringatan Telegram (rekomendasi kurangi ukuran 50%), tidak memblokir trade baru
- ⚠️ Monthly circuit breaker — sama, hanya notifikasi "urgent", tidak ada blocking otomatis di validasi trade baru

### Target Profit & Stop Loss Otomatis
- ✅ 3 skenario target (Conservative 1.5R / Moderate 2.5R / Aggressive 4R) otomatis dari jarak Entry-Stop Loss, opsi "Custom" untuk override manual
- ✅ Watchlist Signal: `stop_loss` dihitung otomatis dari `support_level_2` (bukan persentase risk), konsisten dengan `risk_per_share`

### Support & Resistance 3-Level Otomatis
- ✅ S1-S3 dan R1-R3 dari kombinasi Swing High/Low + Moving Average (MA20/MA50/MA200)
- ✅ Proximity check default 3% (deteksi harga mendekati level S/R)
- ✅ Validasi volume 20 hari (threshold tinggi >1,5x rata-rata, rendah <0,5x)
- ✅ Trend classification 5 kategori (Bullish Kuat/Lemah, Sideways, Bearish Lemah/Kuat) berdasar gap% MA20 vs MA50
- ✅ Tersedia di Trade Journal maupun Watchlist (tombol "Fetch Support/Resistance")

### Konteks Market Regime (IHSG)
- ✅ IHSG (^JKSE) di-refresh otomatis (scheduler tiap 30 menit jam bursa), disimpan di Trading Account Settings (ihsg_trend, ihsg_ma20/50, ihsg_current_price)
- ✅ Histori tersimpan di DocType baru "IHSG Signal" dengan 4 regime: Risk-On, Neutral, Risk-Off, Avoid New Entry
- ⚠️ Regime ini murni informasi — belum mempengaruhi rekomendasi saham individual secara otomatis (riset backtest sedang berjalan untuk memvalidasi apakah layak jadi risk multiplier)

### Price History & Backfill OHLC
- ✅ DocType Price History (ticker, date, timeframe, OHLCV), backfill penuh untuk semua Watchlist + IHSG
- ✅ Refresh harian otomatis (16:30 WIB weekday) + cleanup retensi 365 hari (mingguan)
- ✅ Fondasi untuk chart candlestick dan pattern detection

### Deteksi Pola Chart
- ✅ 6 pola: Double Bottom/Top, Inverse Head & Shoulders/Head & Shoulders, Cup and Handle/Inverted Cup and Handle (Bullish/Bearish)
- ✅ Filter anti-false-positive: separasi minimum antar titik pola, kedalaman pola minimum, pilih kandidat by amplitude terbesar+terbaru
- ✅ Tersimpan di Watchlist Signal (`detected_patterns` JSON, `pattern_summary` teks ringkas), fail-silent, tidak mengubah logic Buy/Sell/Wait/Avoid

### Chart Candlestick Interaktif
- ✅ Tombol "Lihat Chart" di Watchlist dan Watchlist Signal, render via Lightweight Charts (TradingView, CDN)
- ✅ Toggle Daily/Hourly (Hourly masih disabled, "segera hadir")
- ⚠️ Overlay pola chart di atas candlestick — **belum terkonfirmasi muncul**, karena data `detected_patterns` sumbernya field tersimpan (bukan hitung live), dan belum ada Watchlist Signal baru yang berhasil dibuat sejak Pattern Detection deploy
- ⚠️ Bug tampilan saat ganti ticker tanpa refresh halaman (chart bisa "keluar jalur") — fix sudah ditulis, belum dikonfirmasi

### Price Alert
- ✅ Alert terikat wajib ke satu Trade Journal
- ✅ Kondisi >= atau <= terhadap trigger price, dicek scheduler tiap 15 menit jam bursa
- ✅ Auto-fetch ticker dari Trade Journal terkait, auto-update status "Triggered"
- ✅ Pesan Telegram mengingatkan delay data 15-20 menit

### Psikologi Trading
- ✅ Followed System, FOMO, Revenge (checkbox), Emotion/Mistake/Lesson (teks bebas)
- ✅ Compliance rate dihitung otomatis di review harian

### Screening Sinyal Informal
- ✅ Signal Source terpisah dari Trade Journal, status lifecycle New → Screening → Rejected/Promoted to Watchlist
- ⚠️ Reliability score (field ada, read-only) — belum ada logic yang mengisi nilainya

### Watchlist Signal (Rekomendasi Otomatis)
- ✅ Histori rekomendasi Buy/Sell/Wait/Avoid tiap kali Watchlist di-refresh
- ✅ Kolom gabungan "Recom B/S" di list view: Buy → harga Buy (hijau) + Stop Loss; Sell → harga Sell (merah) saja tanpa SL; Wait/Avoid → kosong
- ✅ Warna list view sesuai recommendation dan trend_status
- ✅ `linked_trade` (opsional) untuk mengaitkan ke Trade Journal hasil eksekusi
- ⚠️ `sizing_limiting_factor` dihitung tapi tidak pernah tersimpan (field belum ada di skema + `create_signal()` tidak membaca key ini) — lihat BUG #8

### Analisis Broker Flow (Bandarmologi)
- ✅ Import dari Excel (copy-paste dari Stockbit) dengan parsing posisi cell tetap
- ✅ Auto-parsing angka suffix B/M/K dan koma ribuan
- ✅ Insight otomatis: distribusi/akumulasi besar berdasar ambang ±15% avg_pct
- ✅ Perbandingan harga saat ini vs average price broker, child table detail per broker

### Notifikasi
- ✅ Trade closed, daily review, weekly review, monthly circuit breaker urgent, intraday warning, price alert triggered
- ✅ Semua fail-silent (log error, tidak crash) kalau kredensial/koneksi Telegram bermasalah
- ⚠️ Trade Closed masih terkirim dobel (BUG #1), beberapa pesan masih pakai `\n` literal bukan newline asli (BUG #3 sebagian)

## 2. Fitur Terdaftar di Skema Tapi Belum Diimplementasikan

1. **`risk_per_trade_fast_percent`** (Trading Account Settings) — dimaksudkan untuk mode "fast trading" risiko lebih kecil (0.25% vs 0.5%), belum ada mekanisme pilih mode per trade
2. **`max_sektor_percent`** (Trading Account Settings) — batas eksposur per sektor (30% default), Trade Journal belum punya field "sektor", belum ada `check_sector_exposure()`
3. **`reliability_score`** (Signal Source) — belum ada logic pengisian
4. **`sizing_limiting_factor`** (Watchlist Signal) — dihitung tapi tidak tersimpan (BUG #8)
5. **Overlay pola di chart** — data sudah ada di skema (`detected_patterns`), tapi belum terverifikasi tampil karena isu trigger create_signal (lihat 05_SESSION_LOG.md)

## 3. Ide Pengembangan Lanjutan (Belum Dikerjakan Sama Sekali)

1. **Fase D — Dashboard dengan chart IHSG** — direncanakan sejak awal, belum ada implementasi
2. **Dashboard equity curve** — grafik ekuitas berjalan dari akumulasi `result_rp`
3. **Expectancy calculation** — `(win% × avg_win_R) - (loss% × avg_loss_R)`, metrik lebih berguna dari win rate saja
4. **Regime IHSG sebagai risk multiplier** — sedang diriset lewat backtest (v11.x), belum ada keputusan final soal implementasi ke `risk_engine.py`
5. **Correlation/sektor exposure real** — melengkapi `max_sektor_percent`
6. **Auto-mode "Fast Trading"** — Select field switch `risk_per_trade_percent` vs `risk_per_trade_fast_percent`
7. **Backtesting kualitatif Signal Source** — isi `reliability_score` otomatis dari histori profit sinyal yang di-promote
8. **Report/print format** untuk review mingguan/bulanan (saat ini hanya Telegram)
9. **Validasi struktur Excel sebelum parsing** di `import_from_excel` — cek header sebelum baca data
