# FD-Trade — Daftar Bug

Saya urutkan dari yang paling penting untuk diperbaiki duluan.

> **Status terakhir diverifikasi langsung dari kode di server: 19 September 2026** (setelah patch batch proximity threshold + notif dobel + result_r + parse excel negatif + arsip setup_price_alert.sh).

---

## ✅ BUG #1 — Notifikasi Telegram "Trade Closed" terkirim DUA KALI

> **STATUS (19 Sep 2026): RESOLVED.** `doc_events` di `hooks.py` sudah dihapus (dikomentari dengan penjelasan), cuma `on_update()` di controller yang jalan.

---

## ✅ BUG #2 — `NameError` potensial saat Fetch Support/Resistance gagal di Watchlist

> **STATUS: RESOLVED.** `from frappe import _` sudah ada di `watchlist.py`.

---

## ✅ BUG #3 — Newline literal `\n` tidak ter-render di banyak pesan Telegram

> **STATUS (19 Sep 2026): RESOLVED SEPENUHNYA.** Semua tempat (`daily_review_notification`, `weekly_review_notification`, `check_intraday_conditions`, `notify_on_close`, `generate_insight_notes`) sudah pakai f-string dengan `\n` asli. Catatan sebelumnya bilang `generate_insight_notes` masih literal -- ternyata sudah fix duluan, koreksi status di sini.

---

## ✅ BUG #4 — `Trade Journal.validate()` bisa crash total jika Trading Account Settings belum pernah disimpan

> **STATUS: RESOLVED.** `install.py` `after_install()` sudah auto-create default Trading Account Settings.

---

## ✅ BUG #5 — Skrip `setup_price_alert.sh` bisa menghapus field yang sudah ditambahkan belakangan

> **STATUS (19 Sep 2026): RESOLVED.** File dipindah (`git mv`) ke `archive/setup_price_alert.sh.DO-NOT-RUN`, tidak lagi di root repo tempat mudah dijalankan tidak sengaja.

---

## 🟡 BUG #6 — `risk_r` field tidak pernah dihitung ulang, selalu default 1.0

> **STATUS (19 Sep 2026): MASIH ADA.** Belum diputuskan mau dihapus atau memang didesain sebagai konstanta placeholder. Catatan: `result_r` (hasil aktual) sudah otomatis dihitung per 19 Sep -- `risk_r` yang belum.

---

## 🟡 BUG #7 — Field `risk_per_trade_fast_percent` dan `max_sektor_percent` didefinisikan tapi tidak pernah dipakai

> **STATUS: MASIH ADA.** Butuh keputusan desain: implementasikan mode fast-trading & sector exposure, atau hapus field-nya.

---

## ✅ BUG #8 — `sizing_limiting_factor` dihitung tapi tidak pernah tersimpan

> **STATUS (19 Sep 2026): RESOLVED.** Field sudah ada di `watchlist_signal.json`, `create_signal()` sudah membaca `rec.get("sizing_limiting_factor")`. Koreksi status di sini -- catatan lama masih bilang belum.

---

## ✅ BUG #9 (baru, 19 Sep 2026) — Proximity Threshold di Settings hanya mempengaruhi label, bukan trigger Buy/Sell

> **STATUS: RESOLVED (patch 19 Sep 2026).**

**Lokasi**: `fd_trade/utils/price_data.py` (`calculate_recommendation`), `fd_trade/fd_trade/doctype/watchlist_signal/watchlist_signal.py` (`create_signal`)

`proximity_threshold_pct` dari Trading Account Settings sebelumnya cuma dipakai untuk `get_nearest_level()` (menentukan label "mendekati support/resistance"), sementara `calculate_recommendation()` -- fungsi yang benar-benar menentukan rekomendasi Buy/Sell -- pakai konstanta modul hardcoded `PROXIMITY_THRESHOLD_PCT = 3.0`. Mengubah setting tidak mengubah kapan sistem mengeluarkan sinyal Buy/Sell.

**Fix**: `calculate_recommendation()` sekarang menerima parameter `proximity_threshold_pct`, diteruskan dari `create_signal()` yang sudah punya nilai settings di scope-nya.

---

## ✅ BUG #10 (baru, 19 Sep 2026) — Tombol "Refresh Harga Sekarang" tidak memperbarui Watchlist Signal

> **STATUS: RESOLVED (patch 19 Sep 2026).**

**Lokasi**: `fd_trade/fd_trade/doctype/watchlist/watchlist.py` (`refresh_current_price`)

Beda dengan `fetch_support_resistance` yang sudah memanggil `create_signal()`, `refresh_current_price` sebelumnya hanya update harga tanpa menghitung ulang rekomendasi -- histori Watchlist Signal bisa stale dibanding current_price yang sudah baru.

**Fix**: `refresh_current_price` sekarang juga memanggil `create_signal()` setelah update harga.

---

## ✅ BUG #11 (baru, 19 Sep 2026) — Notifikasi "Trade Closed" terkirim ulang setiap kali trade Closed diedit lagi

> **STATUS: RESOLVED (patch 19 Sep 2026).**

**Lokasi**: `fd_trade/fd_trade/doctype/trade_journal/trade_journal.py` (`on_update`)

Beda dari BUG #1 (dobel kirim dalam satu kali save). Kondisi lama true di setiap save selama status masih Closed -- jadi edit kecil (misal perbaiki "Lesson") di trade yang sudah lama closed memicu notifikasi "Trade Closed" terkirim ulang seolah baru saja ditutup.

**Fix**: ditambahkan cek `self.has_value_changed("status")`, notifikasi hanya terkirim saat transisi Open -> Closed.

---

## 🟢 Fitur Baru (19 Sep 2026) — `result_r` otomatis

Sebelumnya field manual, harus diisi user, rawan human error (lupa isi atau salah hitung), padahal dipakai langsung untuk win rate/total R/max drawdown di review harian-mingguan. Sekarang dihitung otomatis dari `(exit_price - entry_price) / risk_per_share` di `calculate_risk_metrics()`, tetap bisa di-override manual kalau perlu.

---

## 🟢 Perbaikan Kecil (19 Sep 2026) — `parse_excel_value` tangani format negatif akuntansi

`broker_summary.py`: format `(1.5M)` (kurung = negatif, umum di export Excel/Stockbit) sebelumnya gagal parse dan silent return `None` (data hilang tanpa error). Sekarang dideteksi dan dikonversi jadi `-1.5M` dengan benar.

---

## 🟢 Bug Minor / Catatan Kecil

- **`price_data.py`**: `.JK` suffix selalu ditambahkan otomatis (kecuali ticker berawalan `^`) -- kalau ticker sudah mengandung `.JK` manual, akan jadi `BBCA.JK.JK` dan gagal fetch tanpa pesan error jelas.
- **`get_current_price`**: tidak ada jeda antar-request di loop `check_price_alerts`/`refresh_all_watchlist` -- risiko kena limit Yahoo Finance kalau alert/watchlist aktif banyak.
- **`check_consecutive_losses`**: `order_by="date DESC"` tanpa secondary sort -- urutan bisa tidak konsisten kalau ada beberapa trade tanggal sama.
- **`import_from_excel`**: baca posisi cell tetap, rapuh terhadap perubahan format export Stockbit, belum ada validasi struktur sebelum baca.
- **Retensi Watchlist Signal (60 hari) masih hardcoded** di `cleanup_old_watchlist_signals()`, tidak konsisten dengan `cleanup_old_ihsg_signals()` yang sudah pakai `ihsg_signal_retention_days` dari settings. Belum berbahaya, cuma tidak rapi.
