# FD-Trade — Daftar Bug

Saya urutkan dari yang paling penting untuk diperbaiki duluan.

> **Status terakhir diverifikasi langsung dari kode di GitHub: 17 September 2026, 14:20 WIB** (setelah commit `76bf9fba`). Setiap bug di bawah sudah ditandai status terkini — lihat baris **STATUS (17 Sep 2026)** di tiap bug.

---

## 🔴 BUG #1 — Notifikasi Telegram "Trade Closed" terkirim DUA KALI

> **STATUS (17 Sep 2026): MASIH ADA.** Dikonfirmasi ulang langsung dari `trade_journal.py` dan `hooks.py` versi commit `76bf9fba` (16 Sep 23:12 UTC) — commit terbaru sama sekali tidak menyentuh isu ini.

**Lokasi**: `fd_trade/hooks.py` + `fd_trade/fd_trade/doctype/trade_journal/trade_journal.py`

**Penyebab**: Ada dua mekanisme yang sama-sama memanggil `notify_on_close` untuk event yang sama:

1. `hooks.py`:
```python
doc_events = {
    "Trade Journal": {
        "on_update": "fd_trade.fd_trade.doctype.trade_journal.trade_journal.notify_on_close"
    }
}
```
2. Class `TradeJournal` sendiri:
```python
def on_update(self):
    if self.status == "Closed" and self.exit_price and self.result_r is not None:
        notify_on_close(self)
```

Frappe menjalankan **kedua-duanya** saat dokumen di-save: method `on_update()` bawaan controller dipanggil oleh lifecycle Document, DAN hook `doc_events` untuk event yang sama juga dipanggil terpisah oleh framework. Hasilnya: setiap kali trade ditutup dan disimpan ulang (misal edit kecil setelah closed), pesan "Trade Closed" masuk Telegram **dua kali**.

**Dampak**: Bukan bug fatal, tapi mengganggu — apalagi kalau nanti ditambah logic lain di notify_on_close (misal update statistik), efeknya akan double-counted.

**Saran perbaikan**: Pilih satu saja.
- Kalau mau simpel: hapus blok `doc_events` di `hooks.py`, cukup andalkan method `on_update()` di controller.
- Kalau mau eksplisit/terpisah dari model: hapus method `on_update()` dari class `TradeJournal`, biarkan hooks.py saja yang menangani.

---

## ✅ BUG #2 — `NameError` potensial saat Fetch Support/Resistance gagal di Watchlist

> **STATUS (17 Sep 2026): RESOLVED.** Dikonfirmasi `watchlist.py` versi terkini sudah punya `from frappe import _` di bagian import. Kemungkinan diperbaiki saat file ditulis ulang untuk fitur uppercase ticker / auto-fetch, bukan sebagai fix eksplisit — tapi hasil akhirnya sudah benar.

**Lokasi**: `fd_trade/fd_trade/doctype/watchlist/watchlist.py`

```python
@frappe.whitelist()
def fetch_support_resistance(docname):
    from fd_trade.utils.price_data import get_support_resistance
    doc = frappe.get_doc("Watchlist", docname)
    result = get_support_resistance(doc.ticker)
    if not result:
        frappe.throw(_("Gagal mengambil data Support/Resistance untuk ticker {0}. ...").format(doc.ticker))
```

File ini **sebelumnya tidak pernah** melakukan `from frappe import _`. Fungsi `_()` (translation helper) dipakai tanpa di-import — sekarang sudah diperbaiki.

**Dampak (historis)**: Kalau ticker salah ketik atau yfinance gagal fetch (koneksi timeout, ticker delisted, dll), baris `frappe.throw(_(...))` akan gagal dengan `NameError: name '_' is not defined` — user akan melihat traceback error Python mentah alih-alih pesan error yang jelas dalam Bahasa Indonesia.

---

## 🟠 BUG #3 — Newline literal `\n` tidak ter-render di banyak pesan Telegram

> **STATUS (17 Sep 2026): SEBAGIAN RESOLVED.** `daily_review_notification`, `weekly_review_notification`, dan `check_intraday_conditions` di `tasks.py` **sudah diperbaiki** (pakai f-string dengan `\n` asli). **MASIH BELUM diperbaiki**: `notify_on_close()` di `trade_journal.py` dan `generate_insight_notes()` di `broker_summary.py` — keduanya dikonfirmasi masih pakai `\\n` (backslash literal) per commit `76bf9fba`.

**Lokasi tersisa**: `trade_journal.py` (`notify_on_close`), `broker_summary.py` (`generate_insight_notes`)

Contoh di `notify_on_close` (masih seperti ini per 17 Sep 2026):
```python
message = "Trade Closed\\nTicker: " + doc.ticker + "\\nResult R: " + str(doc.result_r) + "R\\nFollowed System: " + followed_status
```

Contoh di `generate_insight_notes` (masih seperti ini per 17 Sep 2026):
```python
insight += "\\nHarga saat ini di bawah rata-rata broker (Rp" + str(self.average_price) + ")"
```

Perhatikan `\\n` — itu backslash ganda dalam source code Python, yang berarti string sebenarnya berisi karakter **backslash literal diikuti huruf n** (`\n` sebagai teks), BUKAN karakter newline.

**Dampak**: Kosmetik tapi cukup mengganggu — notifikasi "Trade Closed" dan insight bandarmologi masih tampil satu baris panjang di Telegram, sementara review harian/mingguan/intraday sudah rapi.

**Saran perbaikan**: Ganti concatenation string di dua fungsi tersisa ini jadi f-string dengan `\n` tunggal (newline asli), konsisten seperti pola yang sudah benar di `check_price_alerts`/`daily_review_notification`.

---

## 🔴 BUG #4 — `Trade Journal.validate()` bisa crash total jika Trading Account Settings belum pernah disimpan

> **STATUS (17 Sep 2026): MASIH ADA.** `install.py` dikonfirmasi masih berisi `after_install()` no-op persis seperti sebelumnya.

**Lokasi**: `trade_journal.py`, method `calculate_risk_metrics` (kini via `risk_engine.calculate_position_sizing()`, tapi root cause sama: bergantung pada `frappe.get_single("Trading Account Settings")` yang butuh dokumen sudah pernah disimpan)

Tidak ada try/except eksplisit untuk kasus dokumen Single belum pernah disimpan. Kalau situs baru di-install dan user langsung mencoba bikin Trade Journal pertama **sebelum** membuka & menyimpan halaman Trading Account Settings sekali, kemungkinan field seperti `modal_total` masih dalam kondisi belum ter-set di database.

**Dampak**: Trade Journal pertama gagal disimpan dengan error yang tidak jelas asal-usulnya bagi user awam.

**Saran perbaikan**: Implementasikan `after_install()` di `fd_trade/install.py` untuk auto-membuat & menyimpan dokumen default Trading Account Settings saat instalasi. Kode di `install.py` bahkan sudah punya komentar yang menandakan ini direncanakan:
```python
def after_install():
    """... Future: could auto-create a default Trading Account Settings record."""
    pass
```
— tapi belum diimplementasikan.

---

## 🟡 BUG #5 — Skrip `setup_price_alert.sh` bisa menghapus field yang sudah ditambahkan belakangan

> **STATUS (17 Sep 2026): MASIH ADA — file masih di root repo (25 KB, terkonfirmasi via GitHub listing).** Belum dihapus/diarsipkan sesuai saran sebelumnya. Risiko makin besar sekarang karena `watchlist_signal.json` dan field-field baru (trend_status, IHSG, dll) sudah jauh lebih banyak dari saat bug ini pertama dicatat.

**Lokasi**: `setup_price_alert.sh` (root repo)

Skrip ini melakukan `cat > trade_journal.json << 'EOF'` yang **menimpa seluruh file**, termasuk field `sr_section`, `support_level`, `resistance_level`, `sr_details` yang belakangan ditambahkan di versi terbaru repo. Kalau skrip lama ini dijalankan lagi tanpa disadari (misal di server baru, atau lupa sudah pernah dijalankan), field Support/Resistance akan **hilang** dari skema.

**Dampak**: Kehilangan data/skema field secara diam-diam, tanpa pesan error apapun — paling berbahaya karena silent.

**Saran perbaikan**: Hapus atau pindahkan `setup_price_alert.sh` keluar dari root repo (atau beri header jelas "JANGAN DIJALANKAN ULANG setelah tanggal X"), supaya tidak tertimpa balik.

---

## 🟡 BUG #6 — `risk_r` field tidak pernah dihitung ulang, selalu default 1.0

> **STATUS (17 Sep 2026): BELUM DIVERIFIKASI ULANG** — tidak ada perubahan terdeteksi di file yang relevan pada commit terbaru. Kemungkinan besar masih berlaku seperti sebelumnya, perlu dicek langsung ke `trade_journal.json` untuk konfirmasi.

**Lokasi**: `trade_journal.json` field `risk_r` (default "1.0", read_only) dan `trade_journal.py`

Field `risk_r` dideklarasikan sebagai "Risk R" read-only dengan default 1.0, tapi tidak ada satupun baris kode yang meng-assign `self.risk_r = ...`. Field ini akan selamanya bernilai 1.0 untuk semua trade.

**Dampak**: Kalau field ini dipakai di laporan/analisis manapun nanti (misal expectancy calculation), datanya akan salah karena selalu 1.0.

**Saran perbaikan**: Perjelas maksud field ini, atau hapus karena redundan dengan definisi R itu sendiri.

---

## 🟡 BUG #7 — Field `risk_per_trade_fast_percent` dan `max_sektor_percent` didefinisikan tapi tidak pernah dipakai

> **STATUS (17 Sep 2026): BELUM DIVERIFIKASI ULANG** — tidak ada perubahan terdeteksi.

**Lokasi**: `trading_account_settings.json`

Dua field ini ada di skema settings tapi tidak direferensikan sama sekali di `trade_journal.py`, `tasks.py`, `risk_engine.py`, atau file manapun.

**Dampak**: Tidak berbahaya, tapi bisa membingungkan user yang mengisi field ini mengira fitur itu aktif.

**Saran perbaikan**: Lihat `04_FITUR.md` — masuk kategori fitur belum selesai, bukan murni bug. Beri catatan di UI (`description`) bahwa field ini belum aktif.

---

## 🆕 BUG #8 — `sizing_limiting_factor` dihitung tapi tidak pernah tersimpan (ditemukan 17 Sep 2026)

**Lokasi**: `fd_trade/utils/price_data.py` (`calculate_recommendation`) + `fd_trade/fd_trade/doctype/watchlist_signal/watchlist_signal.json` + `fd_trade/fd_trade/doctype/watchlist_signal/watchlist_signal.py` (`create_signal`)

**Penyebab**: `calculate_recommendation()` di `price_data.py` menghitung dan mengembalikan `result["sizing_limiting_factor"]` dengan benar (diambil dari `risk_engine.calculate_position_sizing()`). Tapi dua hal terjadi sekaligus:
1. Field `sizing_limiting_factor` **tidak ada** di `field_order`/`fields` skema `watchlist_signal.json`.
2. Fungsi `create_signal()` di `watchlist_signal.py`, saat membangun dict untuk `frappe.get_doc({...})`, **tidak pernah membaca** `rec.get("sizing_limiting_factor")` — key ini tidak ada sama sekali di dict yang dikirim ke `frappe.get_doc`.

Hasilnya: nilai `limiting_factor` yang sudah benar dihitung di memory langsung dibuang begitu saja tanpa error apapun (bukan tersimpan sebagai `None` — memang tidak pernah dicoba disimpan).

**Dampak**: Tidak fatal — user tidak bisa lihat "kenapa lot dibatasi" dari histori Watchlist Signal (hanya bisa lihat pesan `frappe.msgprint` real-time di Trade Journal via `calculate_risk_metrics()`, yang memang sudah punya logic serupa dan benar di sana).

**Saran perbaikan**: Tambahkan field `sizing_limiting_factor` (Select atau Data, read-only) ke `watchlist_signal.json`, lalu tambahkan `"sizing_limiting_factor": rec.get("sizing_limiting_factor")` ke dict di `create_signal()`.

---

## 🟢 Bug Minor / Catatan Kecil

- **`price_data.py`**: `.JK` suffix selalu ditambahkan otomatis (kecuali ticker berawalan `^`, sudah ditangani untuk IHSG) — kalau suatu saat ticker biasa sudah mengandung `.JK` (misal salah input manual), akan jadi `BBCA.JK.JK` dan gagal fetch tanpa pesan error yang jelas ke user (hanya log_error backend).
- **`get_current_price`**: tidak memberi jeda antar-request di loop `check_price_alerts` maupun `refresh_all_watchlist` — kalau alert/watchlist aktif banyak, berisiko kena limit dari Yahoo Finance.
- **`check_consecutive_losses`**: `order_by="date DESC"` tanpa secondary sort — kalau ada beberapa trade dengan tanggal sama, urutan "3 kekalahan beruntun" bisa tidak konsisten antar-run.
- **`import_from_excel`** (`broker_summary.py`): membaca posisi cell tetap (`B7`, `B9`, dst.) — sangat rapuh terhadap perubahan sedikit saja format export dari Stockbit. Tidak ada validasi struktur sebelum mulai membaca (masih belum ada per 17 Sep 2026), jadi kalau format berubah, hasil impor bisa salah tanpa error jelas (silent wrong data), bukan cuma gagal total.
