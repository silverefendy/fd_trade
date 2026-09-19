# FD-Trade — Session Log

> File ini adalah log progres per-sesi (status kerja, isu terbuka, checklist lanjutan) — **berbeda dari** `03_BUGS.md` (daftar bug murni di kode) dan `04_FITUR.md` (daftar fitur final yang sudah selesai). Entri terbaru ditaruh paling atas.

---

## Sesi: Sabtu, 19 September 2026 (Review + Patch Batch — Proximity Threshold, Notif Dobel, Result R Otomatis, Excel Negatif, Arsip Script Lama)

### Konteks
Lanjutan dari review pagi hari ini. Setelah audit ulang lebih teliti, ditemukan bahwa BUG #8 dan sisa BUG #3 (generate_insight_notes) ternyata SUDAH resolved di kode aktual -- koreksi dari klaim awal sesi ini yang salah baca. Juga ditemukan fitur warna list view Watchlist Signal ternyata SUDAH ada sejak sesi sebelumnya (koreksi kedua, sempat salah bilang belum dibuat).

### Temuan Baru & Langsung Dipatch (Batch 1 Script)
Semua dalam 1 script Python (str_replace-style, backup .backup otomatis per file, assert-based supaya gagal keras kalau old_str tidak match), dijalankan user di server, hasil: 5/5 file OK, tidak ada assert error.

1. **BUG #9 (baru) -- Proximity threshold di settings tidak dipakai untuk trigger Buy/Sell.** `calculate_recommendation()` (price_data.py) sebelumnya pakai konstanta hardcoded PROXIMITY_THRESHOLD_PCT, bukan nilai dari Trading Account Settings -- padahal `get_nearest_level()` (untuk label) sudah pakai settings. Fix: tambah parameter `proximity_threshold_pct`, diteruskan dari `create_signal()` (watchlist_signal.py).
2. **BUG #10 (baru) -- Tombol "Refresh Harga Sekarang" tidak memperbarui Watchlist Signal.** `refresh_current_price` (watchlist.py) hanya update harga, tidak panggil `create_signal()` seperti `fetch_support_resistance`. Fix: ditambahkan panggilan `create_signal()`.
3. **BUG #11 (baru) -- notify_on_close terkirim ulang tiap kali trade Closed diedit lagi.** Beda dari BUG #1 lama (dobel dalam satu save). Fix: tambah cek `self.has_value_changed("status")` di `on_update()` (trade_journal.py), notif hanya kirim saat transisi Open -> Closed.
4. **Fitur baru -- `result_r` otomatis.** Sebelumnya manual, rawan human error, padahal dipakai di review harian/mingguan. Fix: dihitung otomatis `(exit_price - entry_price) / risk_per_share` di `calculate_risk_metrics()`, tetap bisa override manual.
5. **Perbaikan kecil -- `parse_excel_value` tangani format negatif akuntansi `(1.5M)`.** Sebelumnya silent return None (data hilang tanpa error). Fix: deteksi kurung, konversi jadi negatif.

### Klarifikasi Status Bug Lama (Koreksi dari Audit Sebelumnya)
- **BUG #8** (sizing_limiting_factor tidak tersimpan) -- **RESOLVED**, ternyata field sudah ada di watchlist_signal.json dan create_signal() sudah membacanya. `03_BUGS.md` versi lama masih salah tercatat sebagai belum.
- **BUG #3 sisa** (generate_insight_notes newline literal) -- **RESOLVED**, sudah pakai f-string `\n` asli dengan comment fix. `03_BUGS.md` versi lama masih salah tercatat sebagai belum.
- **Warna list view Watchlist Signal** -- ternyata **sudah ada** (`watchlist_signal_list.js` lengkap dengan formatter Buy/Sell/Avoid/Wait), bukan belum dibuat seperti dugaan awal sesi ini.

### BUG #5 -- Diselesaikan
`setup_price_alert.sh` dipindah (`git mv`) ke `archive/setup_price_alert.sh.DO-NOT-RUN`, tidak lagi berisiko dijalankan ulang tanpa sengaja dan menimpa skema DocType.

### Verifikasi Server
- `python3 patch_19sep.py` -- 5/5 file OK, backup otomatis dibuat
- `git mv setup_price_alert.sh archive/setup_price_alert.sh.DO-NOT-RUN` -- OK
- `bench restart` -- OK (web + workers + scheduler)
- `bench console` import test (`fd_trade.tasks`, `trade_journal`, `watchlist`, `price_data`) -- OK, tidak ada syntax error
- Tidak perlu `bench migrate` untuk batch ini -- semua perubahan logic Python murni, tidak ada perubahan skema DocType

### Tindakan yang Diambil Sesi Ini
- Patch 5 file (lihat di atas)
- Arsip `setup_price_alert.sh`
- Update `docs/03_BUGS.md` -- koreksi status BUG #3 & #8 jadi RESOLVED, tambah BUG #9/#10/#11 baru, BUG #5 jadi RESOLVED
- Update `docs/05_SESSION_LOG.md` (file ini)

### BELUM Dikerjakan Sesi Ini
- Commit & push ke GitHub -- **harus dilakukan segera setelah ini**, belum ada satupun perubahan hari ini yang ter-push
- BUG #6 (risk_r selalu 1.0) dan BUG #7 (risk_per_trade_fast_percent, max_sektor_percent belum dipakai) -- masih butuh keputusan desain, belum disentuh
- `docs/02_SUMMARY.md` dan `docs/04_FITUR.md` -- masih outdated, belum mencakup Watchlist Signal architecture, risk_engine.py, round_to_tick(), IHSG trend
- Retensi Watchlist Signal (60 hari hardcoded) belum dikonsistenkan dengan pola `ihsg_signal_retention_days` yang sudah configurable

### Checklist Prioritas Sesi Berikutnya
1. Pastikan commit & push hari ini benar-benar sudah masuk ke GitHub (cek `git log`/`git status` di awal sesi berikutnya)
2. Diskusi & putuskan desain BUG #6 (risk_r) dan BUG #7 (risk_per_trade_fast_percent, max_sektor_percent)
3. Tulis ulang `docs/02_SUMMARY.md` dan `docs/04_FITUR.md`
4. Konsistensikan retensi Watchlist Signal dengan pola settings configurable
5. Minor items dari `03_BUGS.md` bagian "Bug Minor" (jeda antar-request yfinance, secondary sort consecutive losses, validasi struktur Excel) -- prioritas rendah, kerjakan kalau ada waktu luang

---

## Sesi: Kamis, 17 September 2026 (Audit Repo — Verifikasi Langsung dari GitHub)

### Konteks
Sesi ini adalah **audit/verifikasi**, bukan pengembangan fitur baru. Tujuannya mengecek klaim di rangkuman sesi sebelumnya ("belum ada satupun commit/push sejak risk engine dimulai") terhadap kondisi nyata repo di GitHub, karena rangkuman tersebut ternyata **sudah kedaluwarsa** — ada commit susulan yang belum tercatat di mana pun.

### Temuan Utama

1. **Commit `76bf9fba` (16 Sep 2026, 23:12 UTC) — "update watchlist dan signal dan hooks"** ternyata sudah mengerjakan sebagian besar item yang sebelumnya ditandai "belum dieksekusi": field `linked_trade`+`stop_loss` di Watchlist Signal, `round_to_tick()` (fraksi harga BEI) di `price_data.py`, kolom "Recom B/S" di `watchlist_signal_list.js`, dan `add_to_apps_screen` di `hooks.py`. Semua terverifikasi live di repo.

2. **Bug ticker uppercase (status "tidak jelas" di rangkuman sebelumnya) — sudah RESOLVED dengan benar.** Fix akhir memakai `before_insert()` (bukan `validate()`), dengan komentar teknis yang menjelaskan urutan pipeline Frappe (`set_new_name()` dipanggil sebelum `run_before_save_methods()`). Ini konsisten dengan root cause yang sudah dianalisis sebelumnya.

3. **BUG #2 (`NameError` di watchlist.py) — RESOLVED.** `from frappe import _` sudah ada.

4. **`refresh_all_watchlist()` di `tasks.py` sudah set `trend_status` dan panggil `create_signal()`** — item checklist yang sebelumnya ditandai "perlu dicek" sudah terkonfirmasi beres.

5. **Ditemukan `docs/05_SESSION_LOG.md` (file ini) sudah ada di repo dari sesi 15-16 Sep**, tapi belum ter-refer di rangkuman sesi yang dipakai untuk melanjutkan kerja — menyebabkan sedikit duplikasi informasi antara rangkuman chat dan file ini. **Rekomendasi ke depan**: jadikan file ini satu-satunya sumber kebenaran progres sesi, jangan andalkan rangkuman chat manual untuk melanjutkan kerja di sesi baru.

6. **Bug yang dikonfirmasi MASIH ADA** (tidak disentuh commit terbaru):
   - BUG #1 — notifikasi Telegram dobel (`trade_journal.py` `on_update()` + `hooks.py` `doc_events`, keduanya masih ada)
   - BUG #3 (sebagian) — `notify_on_close()` dan `generate_insight_notes()` (`broker_summary.py`) masih pakai `\\n` literal, walau `daily/weekly_review_notification` dan `check_intraday_conditions` sudah diperbaiki
   - BUG #4 — `install.py` `after_install()` masih no-op
   - BUG #5 — `setup_price_alert.sh` masih ada di root repo (25 KB), belum diarsipkan/dihapus

7. **Bug baru ditemukan: `sizing_limiting_factor` dihitung tapi tidak pernah tersimpan.** Root cause ganda: field tidak ada di skema `watchlist_signal.json` DAN `create_signal()` tidak membaca key ini dari hasil `calculate_recommendation()`. Detail lengkap di `03_BUGS.md` BUG #8.

### Tindakan yang Diambil Sesi Ini
- Update `docs/03_BUGS.md`: status per-bug ditandai (RESOLVED / PARTIAL / MASIH ADA / BELUM DIVERIFIKASI), tambah BUG #8 baru
- Update `docs/05_SESSION_LOG.md` (file ini)

### BELUM Dikerjakan Sesi Ini (di luar cakupan audit)
- `docs/02_SUMMARY.md` dan `docs/04_FITUR.md` **masih sepenuhnya outdated** — belum menyebut sama sekali arsitektur Watchlist Signal, `risk_engine.py`, `round_to_tick()`, atau IHSG trend yang sudah live di kode. Perlu penulisan ulang signifikan, disarankan sebagai sesi/task terpisah supaya representasinya akurat dan lengkap, bukan tempelan cepat.
- Item-item operasional di server (update SL Trade Journal DEWA ke 318, eksekusi `bench restart` setelah patch, dll) **tidak disentuh sesi ini** — sesi ini murni audit terhadap kode yang sudah ter-push ke GitHub, tidak menyentuh server `it@erpnext` sama sekali (di luar jangkauan akses).

### Checklist Prioritas Sesi Berikutnya (Urutan Disarankan)
1. Patch BUG #1 (pilih salah satu: hapus `doc_events` di hooks.py ATAU hapus method `on_update()` di trade_journal.py)
2. Patch sisa BUG #3 (`notify_on_close` + `generate_insight_notes`, ganti `\\n` jadi f-string dengan `\n` asli)
3. Patch BUG #8 (tambah field `sizing_limiting_factor` + baca di `create_signal()`)
4. Hapus/arsipkan `setup_price_alert.sh` dari root repo (BUG #5)
5. Implementasikan `after_install()` di `install.py` (BUG #4)
6. Tulis ulang `docs/02_SUMMARY.md` dan `docs/04_FITUR.md` supaya mencakup Watchlist Signal, risk_engine, round_to_tick, IHSG trend
7. Verifikasi ulang BUG #6 dan #7 langsung dari `trade_journal.json`/`trading_account_settings.json` (belum dicek di audit ini)
### 18 Sep 2026 -- S/R 3-level, volume, proximity, IHSG regime

- Implementasi bertahap sudah mencakup S1-S3/R1-R3, proximity 3%, validasi volume 20 hari, konteks IHSG, dan histori `IHSG Signal`.
- Threshold volume default: tinggi di atas 1,5x rata-rata dan rendah di bawah 0,5x rata-rata. Sumber harga otomatis tetap yfinance; tidak ada scraping broker, Stockbit, atau IDX.
- Sebelum deploy ke site existing, review migration patch lalu jalankan `bench migrate`; setelah itu jalankan `bench run-tests --app fd_trade` pada environment bench yang aktif.
