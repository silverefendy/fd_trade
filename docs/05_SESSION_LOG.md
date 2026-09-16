# FD-Trade — Session Log

> File ini adalah log progres per-sesi (status kerja, isu terbuka, checklist lanjutan) — **berbeda dari** `03_BUGS.md` (daftar bug murni di kode) dan `04_FITUR.md` (daftar fitur final yang sudah selesai). Entri terbaru ditaruh paling atas.

---

## Sesi: Selasa–Rabu, 15–16 September 2026

### Konteks Server & Preferensi Kerja
- Site: `trace.ciptamebel.co.id`
- Server: SSH `it@erpnext`, bench path `~/frappe/`, app path `~/frappe/apps/fd_trade/fd_trade/`
- Frappe version: 16.30.0
- Preferensi kerja user untuk sesi-sesi berikutnya:
  - Semua patch/script pakai **heredoc** (`cat << 'EOF' ... EOF`), termasuk untuk `bench console`
  - **Tidak pakai** interactive widget/card — jawaban plain text
  - Jangan menimpa seluruh isi file saat edit — pakai `str_replace` / modul `json` Python / `sed` untuk bagian spesifik; selalu backup dulu untuk file JSON DocType
  - `bench console` (IPython) heredoc yang berisi kode berindentasi (try/except, for, if) **wajib** diawali baris `%autoindent off`, kalau tidak parsing gagal karena auto-indent dobel

---

### 🔴 Isu Belum Tuntas #1 — Apps Screen: Tile "FD-Trade" Tidak Muncul

**Root cause (sudah ditemukan):** Layar grid ikon besar ("Apps Screen") di Frappe v16 dikonfigurasi lewat hook `add_to_apps_screen` di `hooks.py`, **bukan** lewat file Workspace JSON. App `nexthd` di server yang sama sudah tampil karena hooks.py-nya punya blok ini; `fd_trade/hooks.py` **tidak punya** blok tersebut sama sekali.

**Sudah diperbaiki di level database (via console), belum di file:**
- Workspace FD-Trade: `parent_page` dikosongkan (tadinya self-referencing)
- `app = fd_trade`, `type = Workspace`, `custom_blocks = []`, `indicator_color = green`, `restrict_to_domain = ""`

**Belum dieksekusi — tambahkan ke `hooks.py`:**
```python
add_to_apps_screen = [
    {
        "name": "fd_trade",
        "logo": "/assets/fd_trade/images/fd_trade-logo.svg",
        "title": "FD-Trade",
        "route": "/desk/fd-trade",
    }
]
```
Lalu `bench build && bench restart`. **Catatan:** route `/desk/fd-trade` masih tebakan, belum terverifikasi.

**Masih perlu:** sinkronkan Workspace fixture (parent_page, app, type, dll — hasil perubahan DB di atas) balik ke file JSON workspace, lalu push ke repo.

---

### 🔴 Isu Belum Tuntas #2 — Bug Ticker Uppercase & Docname (STATUS TIDAK JELAS, PRIORITAS TERTINGGI)

**Root cause 100% terkonfirmasi** (dari pembacaan source code Frappe langsung): Frappe internal memanggil `_sync_autoname_field()` (`base_document.py` ±baris 1247) dari `_validate()` (`document.py` ±baris 595) **setelah** `before_save()` custom kita jalan. Karena `autoname: field:ticker`, docname selalu "menang" atas field ticker — inilah yang menyebabkan ticker uppercase selalu ketimpa balik jadi lowercase.

**Solusi yang direncanakan (2 skenario):**
- **Skenario A (record baru):** pindahkan logic uppercase dari `before_save()` ke `validate()` — untuk dokumen baru, `validate()` dipanggil sebelum naming, jadi docname yang di-generate otomatis sudah kapital, tidak konflik dengan `_sync_autoname_field()`.
- **Skenario B (record lama):** wajib pakai `frappe.rename_doc("Watchlist", self.name, self.ticker, force=True)` untuk rename docname sekaligus — tidak bisa diperbaiki lewat `before_save()`/`db_update()` biasa.

**Status terakhir yang tidak jelas:**
- Skenario A **sudah diimplementasikan** di `watchlist.py` (`validate()`), tapi test insert record baru (`"babp"`) **sebelum restart** masih menghasilkan lowercase.
- Sesi kemudian beralih ke fitur lain (OHLC refresh, trend classification, IHSG) **tanpa sempat verifikasi ulang** apakah fix ini benar-benar bekerja setelah restart.
- `watchlist.py` sudah **berkali-kali ditimpa ulang** sejak itu untuk fitur baru (trend_status, dll) memakai `str_replace` yang mencari blok kode lama — **ada risiko logic uppercase di `validate()` ikut hilang** tanpa disadari.

**Langkah prioritas sesi berikutnya:**
1. Baca ulang `watchlist.py` saat ini — pastikan `validate()` masih berisi `self.ticker = self.ticker.strip().upper()`.
2. Test insert record baru dengan ticker lowercase pendek (misal `"babp"`), cek apakah `name` dan `ticker` hasilnya sudah kapital.
3. Kalau sudah beres → eksekusi backfill `rename_doc()` untuk 3 record lama: `dmas→DMAS`, `bumi→BUMI`, `brms→BRMS` (dry-run sudah dilakukan & dikonfirmasi, eksekusi beneran **belum** dijalankan).
4. Kalau ternyata fix belum bekerja, ulangi analisis (root cause sudah diketahui, tinggal pastikan implementasi konsisten).

> Catatan: user sudah konfirmasi mau **ticker DAN docname (ID)** dua-duanya jadi kapital.

---

### ✅ Fitur Watchlist Baru (Sebagian Besar Selesai, Sebagian Belum Terverifikasi)

1. **Auto-fetch OHLC + current_price + S/R** di Watchlist `before_save()`, trigger saat `is_new()`/ticker berubah.
2. **Scheduled job `refresh_all_watchlist()`** — tiap 15 menit jam bursa, cron `1-59/15 9-16 * * 1-5` di `hooks.py`.
3. **Auto-fetch S/R (termasuk level `_2`)** di Trade Journal `validate()`; scheduled job `refresh_open_trades_sr()` untuk Trade Journal status Open, cron `2-59/30 9-16 * * 1-5`.
4. **Label field via Property Setter:** Support 01/02, Resist 01/02 — tampil benar.
5. **`hide_currency_symbol` Property Setter** — server-side sudah benar; "IDR" yang sempat muncul di UI kemungkinan cache bootinfo browser (**belum dikonfirmasi ulang setelah logout-login**).
6. **Tombol Form View Watchlist** (`watchlist.js`): "Refresh Harga Sekarang" (whitelisted `refresh_current_price`, baru) dan "Fetch Support/Resistance" (existing, diperbaiki agar ikut isi `trend_status`).
7. **Trend Classification** (5 kategori: Bullish Kuat/Lemah, Sideways, Bearish Lemah/Kuat):
   - Field baru `trend_status` (Select, Read Only) di `watchlist.json`.
   - Logic di `get_support_resistance()` (`price_data.py`) — berdasar gap% MA20 vs MA50 (threshold >±2%) + posisi `current_price` vs MA20.
   - Tersimpan via `before_save()`, `fetch_support_resistance()` manual, dan (**perlu dicek**) `refresh_all_watchlist()` scheduler.
   - **Terverifikasi bekerja** untuk BBCA (hasil: Sideways, sesuai hitung manual) dan backfill manual 7 ticker.
   - **Belum dicek:** apakah `refresh_all_watchlist()` di `tasks.py` (ditulis sebelum fitur trend ada) sudah ikut set `trend_status` — kemungkinan besar belum, perlu ditambahkan.
8. **Tombol List View "Refresh Semua Harga"** — `listview.page.add_inner_button` di `watchlist_list.js`, panggil whitelisted wrapper baru `fd_trade.tasks.refresh_all_watchlist_now` — **terverifikasi bekerja**, sekali klik refresh semua record.
9. **Warna List View S/R — sengaja dibalik dari konvensi umum:**
   - Support 01 = merah tua `#c62828`, Support 02 = merah muda `#ef9a9a`
   - Resist 01 = hijau tua `#2e7d32`, Resist 02 = hijau muda `#81c784`
   - Logika: merah = zona beli/oversold, hijau = zona jual/target tercapai (kolom Trend tetap konvensi normal: hijau=bullish, merah=bearish).
   - `current_price` ikut berubah warna kalau mendekati level S/R terdekat (threshold 1%).
   - Diimplementasikan di `watchlist_list.js` (`formatters.current_price`) — **belum dikonfirmasi tampil benar di browser** (perlu screenshot).
10. **IHSG sebagai Market Trend Setter:**
    - `price_data.py`: ticker berawalan `^` (index, misal `^JKSE`) tidak ditambah suffix `.JK`.
    - Field baru di Trading Account Settings: `ihsg_section`, `ihsg_current_price`, `ihsg_trend`, `ihsg_ma20`, `ihsg_ma50`, `ihsg_last_updated`.
    - Fungsi `refresh_ihsg_trend()` + wrapper whitelisted `refresh_ihsg_trend_now()` di `tasks.py`; scheduler cron `3-59/30 9-16 * * 1-5`.
    - **Terverifikasi bekerja** — hasil test: IHSG Trend "Bullish Lemah", current price 6.504.

### Belum Selesai / Menggantung (Tidak Mendesak)
- List View column width — CSS `data-fieldname` selector diterapkan, hasil "agak rapi tapi belum sepenuhnya"; user: *"anggap saja selesai untuk sementara"* — dicatat sebagai isu terbuka, dikerjakan lagi hanya kalau ada waktu luang.
- Price Alert otomatisasi — user pernah bilang "nanti juga dibuat otomatis" tapi belum memilih dari 3 opsi (auto-suggest trigger_price dari S/R / tampilkan info read-only / field snapshot High-Low harian) — **perlu ditanya ulang**.
- Docname Watchlist lama belum di-rename kapital (terkait Isu #2 di atas).
- Forecasting/Market Regime Engine skala penuh (ADX, RSI, backtesting, ML probability) — **sengaja ditunda** oleh user sebagai roadmap terpisah, bukan dikerjakan sekarang.

---

### File yang Dimodifikasi Sepanjang Sesi Ini

| File | Perubahan |
|---|---|
| `fd_trade/fd_trade/doctype/watchlist/watchlist.py` | Uppercase ticker, auto fetch price/OHLC/SR/trend di `before_save()`+`validate()`, fungsi whitelisted baru `fetch_support_resistance()` & `refresh_current_price()` |
| `fd_trade/fd_trade/doctype/watchlist/watchlist.js` | Tombol Form View: "Refresh Harga Sekarang", "Fetch Support/Resistance" |
| `fd_trade/public/js/watchlist_list.js` | Formatters warna (OHLC, S/R dibalik, trend_status, tier, sector, stock_group), tombol List View "Refresh Semua Harga", CSS lebar kolom (partial) |
| `fd_trade/fd_trade/doctype/trade_journal/trade_journal.py` | Uppercase ticker, `_auto_fetch_support_resistance()` di `validate()`, `fetch_support_resistance()` manual diperbaiki isi `_2` |
| `fd_trade/tasks.py` | Fungsi baru: `refresh_all_watchlist()`, `refresh_open_trades_sr()`, `refresh_all_watchlist_now()` (wrapper), `refresh_ihsg_trend()`, `refresh_ihsg_trend_now()` (wrapper) |
| `fd_trade/hooks.py` | Scheduler entries baru untuk semua job di atas (offset menit berbeda-beda); `add_to_apps_screen` **belum** ditambahkan |
| `fd_trade/utils/price_data.py` | Tambah `get_current_ohlc()`, logic trend classification di `get_support_resistance()` (return juga ma20/ma50/trend), dukungan ticker index (prefix `^`) tanpa suffix `.JK` |
| `fd_trade/fd_trade/doctype/watchlist/watchlist.json` | Field baru `trend_status` (Select, Read Only) |
| `fd_trade/fd_trade/doctype/trading_account_settings/trading_account_settings.json` | Field baru `ihsg_section` + 5 field IHSG lainnya |
| Property Setter (via console, bukan file) | Label rename, `hide_currency_symbol`, columns/width Watchlist |
| List View Settings Watchlist (DocType record) | Sudah termasuk `trend_status`; Report "Watchlist Ringkas" (Report Builder) |

> ⚠️ Status push ke repo: entri ini sendiri (`docs/05_SESSION_LOG.md`) dipush lewat GitHub connector. File-file kode di atas (watchlist.py, watchlist.js, watchlist_list.js, tasks.py, hooks.py, price_data.py, kedua JSON DocType) **masih perlu dicek statusnya di repo** — kalau belum ada, push manual dari server terlebih dulu sebelum lanjut ke checklist berikutnya.

---

### Checklist Prioritas Sesi Berikutnya (Urutan)

1. **[PALING PRIORITAS]** Re-verifikasi bug ticker uppercase — cek apakah fix `validate()` masih ada di `watchlist.py` versi terkini, test insert record baru lagi, baru putuskan lanjut backfill `rename_doc()` atau tidak.
2. Cek apakah `refresh_all_watchlist()` di `tasks.py` sudah set `trend_status` juga — kalau belum, tambahkan.
3. Konfirmasi visual: warna Support/Resist terbalik dan highlight `current_price` sudah tampil benar di browser (minta screenshot).
4. Tambahkan `add_to_apps_screen` ke `hooks.py` untuk fix Apps Screen tile, `bench build && bench restart`, verifikasi route yang benar.
5. Sinkronkan Workspace fixture (parent_page, app, type, dll) dari database ke file JSON, push ke GitHub.
6. Push semua perubahan kode sesi ini ke GitHub (kalau belum).
7. Minta user logout-login, cek ulang status "IDR" di UI.
8. Tanya user preferensi otomatisasi Price Alert (3 opsi).
9. Kerjakan patch 7 bug prioritas tinggi dari `docs/03_BUGS.md` (belum ada satupun yang dipatch).
10. Revisit List View column width kalau ada waktu (tidak mendesak).
