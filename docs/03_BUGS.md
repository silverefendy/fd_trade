# FD-Trade — Daftar Bug

Saya urutkan dari yang paling penting untuk diperbaiki duluan.

---

## 🔴 BUG #1 — Notifikasi Telegram "Trade Closed" terkirim DUA KALI

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

## 🔴 BUG #2 — `NameError` potensial saat Fetch Support/Resistance gagal di Watchlist

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

File ini **tidak pernah** melakukan `from frappe import _`. Fungsi `_()` (translation helper) dipakai tanpa di-import. Bandingkan dengan `trade_journal.py` yang punya `from frappe import _` di baris atas.

**Dampak**: Kalau ticker salah ketik atau yfinance gagal fetch (koneksi timeout, ticker delisted, dll), baris `frappe.throw(_(...))` akan gagal dengan `NameError: name '_' is not defined` — user akan melihat traceback error Python mentah alih-alih pesan error yang jelas dalam Bahasa Indonesia. Ironisnya, justru di jalur *error handling* itulah bug ini muncul — jadi tepat saat sistem seharusnya memberi pesan jelas, malah crash dengan cara yang membingungkan.

**Saran perbaikan**: Tambahkan `from frappe import _` di bagian import `watchlist.py`.

---

## 🟠 BUG #3 — Newline literal `\n` tidak ter-render di banyak pesan Telegram

**Lokasi**: `trade_journal.py` (`notify_on_close`), `tasks.py` (`daily_review_notification`, `weekly_review_notification`, `check_intraday_conditions`), `broker_summary.py` (`generate_insight_notes`)

Contoh di `notify_on_close`:
```python
message = "Trade Closed\\nTicker: " + doc.ticker + "\\nResult R: " + str(doc.result_r) + "R\\nFollowed System: " + followed_status
```

Perhatikan `\\n` — itu backslash ganda dalam source code Python, yang berarti string sebenarnya berisi karakter **backslash literal diikuti huruf n** (`\n` sebagai teks), BUKAN karakter newline. Efeknya, pesan Telegram akan tampil sebagai satu baris panjang:
```
Trade Closed\nTicker: BBCA\nResult R: 1.5R\nFollowed System: Yes
```
alih-alih:
```
Trade Closed
Ticker: BBCA
Result R: 1.5R
Followed System: Yes
```

**Perbandingan**: fungsi `check_price_alerts` di `tasks.py` justru menulis dengan benar pakai f-string dan `\n` tunggal (newline asli) — jadi inkonsistensi ini murni karena penulisan manual string concatenation di beberapa tempat vs f-string di tempat lain.

**Dampak**: Kosmetik tapi cukup mengganggu — hampir semua notifikasi utama (trade closed, daily/weekly review, intraday warning, insight bandarmologi) jadi susah dibaca di Telegram.

**Saran perbaikan**: Ganti semua concatenation string yang pakai `"\\n"` jadi f-string dengan `"\n"` tunggal, konsisten seperti pola di `check_price_alerts`.

---

## 🟠 BUG #4 — `Trade Journal.validate()` bisa crash total jika Trading Account Settings belum pernah disimpan

**Lokasi**: `trade_journal.py`, method `calculate_risk_metrics`

```python
def calculate_risk_metrics(self):
    settings = frappe.get_single("Trading Account Settings")
    risk_per_share = self.entry_price - self.stop_loss
    ...
```

Tidak ada try/except di sini, berbeda dengan `telegram.py` yang secara eksplisit menangani `frappe.DoesNotExistError`. Kalau situs baru di-install dan user langsung mencoba bikin Trade Journal pertama **sebelum** membuka & menyimpan halaman Trading Account Settings sekali, kemungkinan field seperti `modal_total` masih dalam kondisi belum ter-set di database (tergantung apakah Frappe sudah auto-insert default Single doc saat install — ini tidak konsisten antar versi Frappe).

**Dampak**: Trade Journal pertama gagal disimpan dengan error yang tidak jelas asal-usulnya bagi user awam.

**Saran perbaikan**: Tambahkan pengecekan eksplisit di `after_install()` (`fd_trade/install.py`, saat ini masih kosong/no-op) untuk auto-membuat & menyimpan dokumen default Trading Account Settings saat instalasi. Kode di `install.py` bahkan sudah punya komentar:
```python
def after_install():
    """... Future: could auto-create a default Trading Account Settings record."""
    pass
```
— tapi belum diimplementasikan.

---

## 🟡 BUG #5 — Skrip `setup_price_alert.sh` bisa menghapus field yang sudah ditambahkan belakangan

**Lokasi**: `setup_price_alert.sh`

Skrip ini melakukan `cat > trade_journal.json << 'EOF'` yang **menimpa seluruh file**, termasuk field `sr_section`, `support_level`, `resistance_level`, `sr_details` yang belakangan ditambahkan di versi terbaru repo. Kalau skrip lama ini dijalankan lagi tanpa disadari (misal di server baru, atau lupa sudah pernah dijalankan), field Support/Resistance akan **hilang** dari skema.

**Dampak**: Kehilangan data/skema field secara diam-diam, tanpa pesan error apapun — paling berbahaya karena silent.

**Saran perbaikan**: Setelah dijalankan sekali dan berhasil migrate, hapus atau pindahkan `setup_price_alert.sh` keluar dari root repo (atau beri header jelas "JANGAN DIJALANKAN ULANG setelah tanggal X"), supaya tidak tertimpa balik.

---

## 🟡 BUG #6 — `risk_r` field tidak pernah dihitung ulang, selalu default 1.0

**Lokasi**: `trade_journal.json` field `risk_r` (default "1.0", read_only) dan `trade_journal.py`

Field `risk_r` dideklarasikan sebagai "Risk R" read-only dengan default 1.0, tapi tidak ada satupun baris kode di `calculate_risk_metrics()` atau method lain yang meng-assign `self.risk_r = ...`. Field ini akan selamanya bernilai 1.0 untuk semua trade, tidak peduli seberapa besar risiko aktualnya berbeda dari yang direncanakan.

**Dampak**: Kalau field ini dipakai di laporan/analisis manapun nanti (misal expectancy calculation), datanya akan salah karena selalu 1.0.

**Saran perbaikan**: Perjelas maksud field ini — apakah harusnya "R risiko yang direncanakan" (selalu 1.0 by definition karena R = jarak entry-SL adalah 1 unit risiko) atau field ini semestinya dihapus karena redundan dengan definisi R itu sendiri.

---

## 🟡 BUG #7 — Field `risk_per_trade_fast_percent` dan `max_sektor_percent` didefinisikan tapi tidak pernah dipakai

**Lokasi**: `trading_account_settings.json`

Dua field ini ada di skema settings tapi tidak direferensikan sama sekali di `trade_journal.py`, `tasks.py`, atau file manapun. Sepertinya fitur "fast trading mode" (risk lebih kecil untuk fast trade) dan "batas eksposur per sektor" direncanakan tapi belum diimplementasikan.

**Dampak**: Tidak berbahaya, tapi bisa membingungkan user yang mengisi field ini mengira fitur itu aktif, padahal tidak ada efek apapun terhadap validasi.

**Saran perbaikan**: Lihat `04_FITUR.md` — ini masuk kategori fitur belum selesai, bukan murni bug, tapi sebaiknya diberi catatan di UI (`description`) bahwa field ini belum aktif, kalau memang belum mau diimplementasikan sekarang.

---

## 🟢 Bug Minor / Catatan Kecil

- **`price_data.py`**: `.JK` suffix selalu ditambahkan otomatis — kalau suatu saat ticker sudah mengandung `.JK` (misal salah input manual), akan jadi `BBCA.JK.JK` dan gagal fetch tanpa pesan error yang jelas ke user (hanya log_error backend).
- **`get_current_price`**: tidak memberi jeda antar-request di loop `check_price_alerts` — kalau alert aktif banyak (puluhan), berisiko kena limit dari Yahoo Finance.
- **`check_consecutive_losses`**: `order_by="date DESC"` tanpa secondary sort — kalau ada beberapa trade dengan tanggal sama, urutan "3 kekalahan beruntun" bisa tidak konsisten antar-run karena urutan hasil query tidak deterministik untuk baris dengan nilai sort yang sama.
- **`import_from_excel`** (`broker_summary.py`): membaca posisi cell tetap (`B7`, `B9`, dst.) — sangat rapuh terhadap perubahan sedikit saja format export dari Stockbit. Tidak ada validasi struktur sebelum mulai membaca, jadi kalau format berubah, hasil impor bisa salah tanpa error jelas (silent wrong data), bukan cuma gagal total.
