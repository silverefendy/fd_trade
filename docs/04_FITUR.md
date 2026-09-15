# FD-Trade — Daftar Fitur

## 1. Fitur yang Sudah Ada & Berfungsi

### Manajemen Risiko
- ✅ Position sizing otomatis berdasar % risiko tetap dari modal
- ✅ Suggested lot otomatis (dibulatkan ke bawah kelipatan 100 lembar)
- ✅ Peringatan (bukan blokir) kalau posisi aktual melebihi 120% dari risiko yang disarankan
- ✅ Daily loss limit — blokir trade baru kalau limit harian terlampaui
- ✅ Consecutive loss circuit breaker — blokir trade baru setelah N kekalahan beruntun
- ✅ Per-stock exposure limit — blokir kalau eksposur ke satu ticker berlebihan
- ✅ Total portfolio exposure limit
- ⚠️ Weekly loss limit — **hanya mengirim peringatan Telegram** (rekomendasi kurangi ukuran 50%), TIDAK memblokir trade baru seperti daily limit. Ini kemungkinan disengaja (soft warning vs hard block), tapi perlu dikonfirmasi apakah ini memang desain yang diinginkan.
- ⚠️ Monthly circuit breaker — sama, hanya notifikasi "urgent", tidak ada blocking mechanism otomatis di level validasi trade baru.

### Target Profit Otomatis
- ✅ Perhitungan 3 skenario target (Conservative 1.5R / Moderate 2.5R / Aggressive 4R) otomatis dari jarak Entry-Stop Loss
- ✅ Opsi "Custom" untuk override manual
- ✅ Ditampilkan sebagai teks suggestion di field read-only

### Support & Resistance Otomatis
- ✅ Kombinasi Swing High/Low (window 5 hari, histori 6 bulan) + Moving Average (MA20/MA50/MA200)
- ✅ Tersedia baik di Trade Journal maupun Watchlist (tombol "Fetch Support/Resistance")
- ✅ Detail perhitungan ditampilkan sebagai teks (harga saat ini, swing S/R, tiap MA)

### Price Alert
- ✅ Alert terikat wajib ke satu Trade Journal (tidak bisa berdiri sendiri)
- ✅ Kondisi >= atau <= terhadap trigger price
- ✅ Auto-fetch ticker dari Trade Journal terkait
- ✅ Dicek scheduler tiap 15 menit jam bursa, auto-update status jadi "Triggered"
- ✅ Pesan Telegram mengingatkan delay data 15-20 menit — konfirmasi manual sebelum eksekusi

### Psikologi Trading
- ✅ Followed System (checkbox kepatuhan)
- ✅ FOMO, Revenge (checkbox)
- ✅ Emotion, Mistake, Lesson (teks bebas)
- ✅ Compliance rate dihitung otomatis di review harian (% trade yang followed_system)

### Screening Sinyal Informal
- ✅ Signal Source terpisah dari Trade Journal — tidak bisa langsung jadi entry tanpa proses screening manual
- ✅ Status lifecycle: New → Screening → Rejected / Promoted to Watchlist
- ✅ Reliability score (field ada, read-only) — namun **belum ada logic yang mengisi nilainya** (lihat bagian "Belum Selesai" di bawah)

### Analisis Broker Flow (Bandarmologi)
- ✅ Import dari Excel (copy-paste dari Stockbit) dengan parsing posisi cell tetap
- ✅ Auto-parsing angka dengan suffix B/M/K dan koma ribuan
- ✅ Insight otomatis: label distribusi/akumulasi besar berdasar ambang ±15% avg_pct
- ✅ Perbandingan harga saat ini vs average price broker
- ✅ Child table detail per broker (buy/sell side)

### Notifikasi
- ✅ Trade closed
- ✅ Daily review (jumlah trade, win/loss, total P&L, compliance rate)
- ✅ Weekly review (win rate, total R, max drawdown, jumlah FOMO/revenge)
- ✅ Monthly circuit breaker urgent alert
- ✅ Intraday warning (weekly loss & total exposure)
- ✅ Price alert triggered
- ✅ Semua fail-silent (log error, tidak crash proses utama) kalau kredensial/koneksi Telegram bermasalah — desain defensif yang bagus

## 2. Fitur yang Terdaftar di Skema Tapi Belum Diimplementasikan

Ini bukan bug — field-nya ada dan valid, tapi logic pemakaiannya belum ditulis:

1. **`risk_per_trade_fast_percent`** (Trading Account Settings) — sepertinya dimaksudkan untuk mode "fast trading" dengan risiko lebih kecil (0.25% vs 0.5% normal), tapi tidak ada mekanisme di Trade Journal untuk memilih mode "fast" vs "normal" per trade, dan `calculate_risk_metrics()` selalu pakai `risk_per_trade_percent` biasa.

2. **`max_sektor_percent`** (Trading Account Settings) — batas eksposur per sektor (30% default), tapi:
   - Trade Journal tidak punya field "sektor" sama sekali (hanya Watchlist yang punya field `sector`)
   - Tidak ada fungsi `check_sector_exposure()` di `trade_journal.py`

3. **`reliability_score`** (Signal Source) — field read-only untuk skor keandalan sumber sinyal, tapi tidak ada logic apapun (manual maupun otomatis) yang menghitung/mengisi nilai ini.

4. **Field "sektor" di Trade Journal** — tidak ada, padahal dibutuhkan kalau mau mengimplementasikan poin #2 di atas.

## 3. Ide Pengembangan Lanjutan (Saran, Belum Ada Sama Sekali)

Sebagai trader-developer, ini beberapa hal yang menurut saya akan menambah nilai signifikan:

1. **Dashboard equity curve** — grafik ekuitas berjalan dari akumulasi `result_rp`, akan sangat membantu melihat drawdown visual dibanding hanya baca angka di notifikasi mingguan.

2. **Expectancy calculation** — dengan data win rate + average win + average loss yang sudah ada di sistem, expectancy per-R (`(win% × avg_win_R) - (loss% × avg_loss_R)`) adalah metrik jauh lebih berguna daripada sekadar win rate untuk menilai apakah sistem trading benar-benar profitable secara statistik.

3. **Correlation/sektor exposure real** — melengkapi `max_sektor_percent` yang sudah ada di settings tapi belum aktif (lihat bagian 2 di atas), termasuk field sektor di Trade Journal.

4. **Auto-mode "Fast Trading"** — Select field di Trade Journal untuk pilih "Normal" atau "Fast", yang otomatis switch risk percent antara `risk_per_trade_percent` dan `risk_per_trade_fast_percent`.

5. **Backtesting kualitatif dari histori Signal Source** — tracking berapa persen sinyal dari tiap `source_name` yang akhirnya profitable setelah di-promote ke Watchlist lalu jadi Trade Journal — ini akan mengisi `reliability_score` secara otomatis dan objektif, bukan manual.

6. **Report/print format khusus** untuk review mingguan/bulanan (saat ini hanya Telegram, tidak ada versi PDF/print yang bisa diarsipkan formal).

7. **Validasi struktur Excel sebelum parsing** di `import_from_excel` — cek dulu apakah cell tertentu memang berisi header yang diharapkan sebelum mulai baca data, supaya gagal cepat dengan pesan jelas kalau format berubah, bukan diam-diam salah baca.
