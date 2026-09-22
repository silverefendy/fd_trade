"""
Trade Journal Controller
Core logging doctype for trading entries with risk management validation
dan perhitungan target price otomatis berbasis R-multiple.
"""

import frappe
from fd_trade.utils.price_data import calculate_atr
from frappe.model.document import Document
from frappe import _

# Kategori target price berbasis R-multiple.
# R = jarak Entry Price ke Stop Loss.
# Angka ini adalah kerangka matematis, BUKAN jaminan/prediksi pergerakan harga.
TARGET_CATEGORIES = {
    "Conservative (1.5R)": 1.5,
    "Moderate (2.5R)": 2.5,
    "Aggressive (4R)": 4.0,
}


class TradeJournal(Document):
    """Trade Journal entry with risk management and psychology tracking."""

    def autoname(self):
        """Custom naming (22 Sep 2026): format tampil TRX-YYMMDD-#### (pakai
        tanggal Entry, field `date` -- BUKAN tanggal hari ini/creation), tapi
        counter RESET PER BULAN (bukan per hari), supaya nomor urut tetap
        berguna untuk menghitung 'berapa transaksi bulan ini'.

        Dicapai dgn pisah antara:
        - series_key: TRX-YYMM (mis. TRX-2609) -> ini yg dipakai getseries()
          utk nomor urut, jadi counter reset tiap awal bulan baru
        - nama tampil akhir: TRX-YYMMDD-#### (tanggal lengkap dari field date,
          tapi nomor urut tetap ambil dari counter bulanan di atas)

        WAJIB self.date sudah terisi (field ini reqd=1 di schema, jadi
        seharusnya selalu ada saat autoname dipanggil)."""
        from frappe.model.naming import getseries
        from frappe.utils import getdate

        if not self.date:
            frappe.throw(_("Tanggal (Date) wajib diisi sebelum trade bisa disimpan."))

        d = getdate(self.date)
        yymm = d.strftime("%y%m")
        yymmdd = d.strftime("%y%m%d")

        series_key = f"TRX-{yymm}-"
        counter = getseries(series_key, 4)  # 4 digit, reset tiap key (bulan) baru

        self.name = f"TRX-{yymmdd}-{counter}"

    def validate(self):
        """Validate trade entry and calculate risk metrics."""
        if self.ticker:
            self.ticker = self.ticker.strip().upper()
        self._auto_fill_market_regime()

        # Urutan penting (22 Sep 2026): watchlist dulu -> S/R -> stop loss
        # auto -> baru risk metrics, karena tiap tahap butuh data dari
        # tahap sebelumnya (target TP "Resistance (Auto)" butuh S/R,
        # risk metrics butuh stop_loss).
        self._auto_create_watchlist_if_missing()

        # FIX (22 Sep 2026): sebelumnya cuma trigger saat ticker baru/berubah,
        # jadi current_price selamanya kosong untuk record LAMA yang dibuat
        # sebelum field ini ada. Tambah kondisi "current_price masih kosong"
        # supaya record lama ikut terisi di save berikutnya.
        if self.is_new() or self.has_value_changed("ticker") or not self.current_price:
            self._auto_fetch_support_resistance()

        if self.is_new() and not self.stop_loss:
            self._auto_calculate_stop_loss()

        self.calculate_risk_metrics()

        if self.is_new():
            self.check_risk_management_rules()

    def _auto_fill_market_regime(self):
        """Isi Market Regime otomatis dari IHSG Trend (Trading Account
        Settings), BUKAN manual pilih -- keputusan trader tetap manual
        (entry/exit/stop loss), tapi data konteks pasar ini otomatis.
        Dipetakan 5 kategori IHSG -> 3 kategori Trade Journal (22 Sep 2026)."""
        settings = frappe.get_single("Trading Account Settings")
        ihsg_trend = settings.ihsg_trend
        mapping = {
            "Bullish Kuat": "Bull",
            "Bullish Lemah": "Bull",
            "Sideways": "Sideways",
            "Bearish Lemah": "Bear",
            "Bearish Kuat": "Bear",
        }
        if ihsg_trend in mapping:
            self.market_regime = mapping[ihsg_trend]

    def _auto_create_watchlist_if_missing(self):
        """Kalau ticker belum ada di Watchlist, buat otomatis (tier default
        'C' -- ticker ini masuk lewat entry langsung, bukan lewat proses
        screening manual biasa, jadi jujur beri tier terendah). Fail-silent:
        kalau gagal, trade tetap lanjut disimpan, S/R & stop loss auto akan
        kosong sampai Watchlist-nya ada (ditangani fallback masing-masing)."""
        if not self.ticker:
            return
        if frappe.db.exists("Watchlist", self.ticker):
            return
        try:
            wl = frappe.get_doc({
                "doctype": "Watchlist",
                "ticker": self.ticker,
                "tier": "C",
            })
            wl.insert(ignore_permissions=True)
            frappe.msgprint(
                _("Ticker {0} belum ada di Watchlist, entry baru dibuat otomatis (Tier C).").format(self.ticker),
                indicator="blue"
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Auto-create Watchlist gagal untuk {self.ticker}")

    def _auto_calculate_stop_loss(self):
        """Hitung Stop Loss otomatis, prioritas (disepakati 21 Sep 2026):
        1. Watchlist Signal terbaru dgn rekomendasi Buy utk ticker ini
        2. Hitung ulang ATR14 x 1.5 langsung dari Price History (reuse
           calculate_atr(), konsisten dgn hasil backtest 750 hari)
        3. Fallback Support Level 2 (struktural) kalau ATR gagal dihitung
        Kalau semua gagal (ticker baru, data historis <14 hari), stop_loss
        dibiarkan kosong -- trade tetap tersimpan (lihat guard di
        calculate_risk_metrics), user isi manual & Save ulang nanti."""
        if not self.entry_price:
            return

        latest_signal = frappe.get_all(
            "Watchlist Signal",
            filters={"ticker": self.ticker, "recommendation": "Buy"},
            fields=["stop_loss"],
            order_by="creation desc",
            limit=1
        )
        if latest_signal and latest_signal[0].stop_loss:
            self.stop_loss = latest_signal[0].stop_loss
            return

        try:
            from fd_trade.utils.volume_profile import get_price_history_rows
            rows = get_price_history_rows(self.ticker, lookback_days=250)
            atr14 = calculate_atr(rows) if rows else None
            if atr14:
                self.stop_loss = self.entry_price - (atr14 * 1.5)
                return
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Auto SL (ATR) gagal untuk {self.ticker}")

        if self.support_level_2:
            self.stop_loss = self.support_level_2

    def _auto_fetch_support_resistance(self):
        """Ambil Support/Resistance otomatis dari yfinance saat ticker baru
        diisi atau diganti, fail-silent (tidak menghentikan proses save
        kalau yfinance gagal/timeout)."""
        if not self.ticker:
            return

        # Current Price: disalin dari Watchlist (BUKAN fetch yfinance sendiri
        # di Trade Journal -- keputusan arsitektur 22 Sep 2026). Kalau ticker
        # belum ada di Watchlist, current_price tetap kosong.
        watchlist_price = frappe.db.get_value("Watchlist", self.ticker, "current_price")
        if watchlist_price:
            self.current_price = watchlist_price

        # Trend (22 Sep 2026): salin apa adanya dari Watchlist, JANGAN hitung
        # ulang di sini -- Watchlist sudah jadi satu-satunya sumber kebenaran
        # utk klasifikasi MA20 vs MA50 (lihat trend_status di watchlist.py).
        watchlist_trend = frappe.db.get_value("Watchlist", self.ticker, "trend_status")
        if watchlist_trend:
            self.trend = watchlist_trend

        from fd_trade.utils.price_data import get_support_resistance

        result = get_support_resistance(self.ticker)
        if result:
            self.support_level = result["support_level"]
            self.support_level_2 = result["support_level_2"]
            self.support_level_3 = result["support_level_3"]
            self.resistance_level = result["resistance_level"]
            self.resistance_level_2 = result["resistance_level_2"]
            self.resistance_level_3 = result["resistance_level_3"]
            self.sr_details = result["details"]

    def calculate_risk_metrics(self):
        """Calculate risk amount, suggested lot, target price suggestions,
        dan validasi stop loss. Menggunakan risk_engine.py sebagai satu-satunya
        sumber kebenaran, konsisten dengan Watchlist Signal -- lot yang
        disarankan sudah mempertimbangkan max_per_stock_percent dan
        max_exposure_percent, bukan cuma risk_per_trade_percent saja."""
        from fd_trade.utils.risk_engine import calculate_position_sizing

        # Kalau stop_loss masih kosong (auto-calc gagal semua & user belum
        # isi manual), JANGAN blokir save -- simpan trade tanpa validasi
        # risiko dulu, tunggu data tersedia / isi manual lalu Save ulang.
        if not self.stop_loss:
            frappe.msgprint(
                _("Stop Loss belum bisa dihitung otomatis untuk {0} (data S/R & ATR belum tersedia). Trade tetap disimpan TANPA validasi risiko -- isi Stop Loss manual lalu Save ulang begitu data tersedia.").format(self.ticker),
                indicator="red"
            )
            self.risk_amount = None
            self.suggested_lot = None
            return

        # Calculate risk per share
        risk_per_share = self.entry_price - self.stop_loss

        if risk_per_share <= 0:
            frappe.throw(_("Stop loss must be below entry price for long positions."))

        # exclude_docname mencegah trade ini menghitung dirinya sendiri
        # dobel sebagai "eksposur existing" saat sedang di-edit (bukan baru)
        exclude_docname = None if self.is_new() else self.name

        sizing = calculate_position_sizing(
            ticker=self.ticker,
            current_price=self.entry_price,
            risk_per_share=risk_per_share,
            exclude_docname=exclude_docname,
            trading_mode=self.trading_mode or "Normal",
        )

        if not sizing:
            frappe.throw(_("Gagal menghitung risk sizing. Cek apakah Trading Account Settings sudah diisi Modal Total."))

        risk_rp = sizing["risk_amount"]
        self.risk_amount = risk_rp
        self.suggested_lot = sizing["final_lot"]

        # Transparan: kasih tahu kalau lot dibatasi bukan oleh risk murni,
        # tapi oleh kuota per-saham/eksposur total -- supaya tidak
        # membingungkan kenapa suggested_lot lebih kecil dari perkiraan
        # berbasis risk_per_trade_percent saja.
        if sizing["limiting_factor"] != "risk" and sizing["final_lot"] < sizing["lot_by_risk"]:
            factor_label = {
                "max_per_stock": _("batas maksimal per saham"),
                "max_exposure": _("batas maksimal eksposur portofolio"),
            }.get(sizing["limiting_factor"], sizing["limiting_factor"])
            frappe.msgprint(
                _("Suggested lot dibatasi oleh {0} ({1} lot), bukan murni dari risk per trade ({2} lot).").format(
                    factor_label, sizing["final_lot"], sizing["lot_by_risk"]
                ),
                indicator="orange"
            )

        # Warn if actual position exceeds suggested risk
        if self.position_lot:
            actual_risk = self.position_lot * 100 * risk_per_share
            if actual_risk > risk_rp * 1.2:  # 20% tolerance
                frappe.msgprint(
                    _("Warning: Actual risk ({0}) exceeds suggested risk ({1}) by more than 20%.").format(
                        frappe.format_value(actual_risk, {"fieldtype": "Currency"}),
                        frappe.format_value(risk_rp, {"fieldtype": "Currency"})
                    )
                )

        # ---- Target Price otomatis berbasis R-multiple ----
        self.calculate_target_price(risk_per_share)

        # Calculate result_rp if exit_price is set
        if self.exit_price and self.position_lot:
            self.result_rp = (self.exit_price - self.entry_price) * self.position_lot * 100

        # Auto-hitung result_r dari R-multiple, tetap bisa di-override manual.
        if self.exit_price and risk_per_share:
            self.result_r = (self.exit_price - self.entry_price) / risk_per_share

    def calculate_target_price(self, risk_per_share):
        """Hitung 3 skenario target profit (Conservative/Moderate/Aggressive)
        berdasarkan R-multiple, tampilkan sebagai suggestion, dan set
        target_price otomatis kecuali kategori 'Custom' dipilih."""

        suggestion_lines = []
        computed = {}

        for label, multiple in TARGET_CATEGORIES.items():
            price = self.entry_price + (risk_per_share * multiple)
            computed[label] = price
            suggestion_lines.append(f"{label}: Rp{price:,.0f}  (jika TP tercapai = +{multiple}R)")

        # Resistance (Auto): target profit dari struktur harga (S/R), BUKAN
        # R-multiple -- titik tengah Resistance 1-2, fallback ke Resistance 1
        # saja kalau Resistance 2 belum ada datanya. Belum diuji backtest
        # (beda dgn ATR-stop yg sudah lewat backtest 750 hari) -- starting
        # point yg bisa dikoreksi kalau data live menunjukkan A/B lebih baik.
        resistance_auto_price = None
        if self.resistance_level:
            if self.resistance_level_2:
                resistance_auto_price = (self.resistance_level + self.resistance_level_2) / 2
            else:
                resistance_auto_price = self.resistance_level
        if resistance_auto_price:
            suggestion_lines.append(
                f"Resistance (Auto): Rp{resistance_auto_price:,.0f}  (titik tengah R1-R2, fallback R1 kalau R2 kosong)"
            )

        self.target_suggestions = "\n".join(suggestion_lines)

        # Kalau kategori bukan Custom, auto-isi target_price.
        # Kalau Custom, biarkan nilai yang sudah diinput user (tidak ditimpa).
        if self.target_category and self.target_category != "Custom":
            if self.target_category == "Resistance (Auto)":
                if resistance_auto_price:
                    self.target_price = resistance_auto_price
                # kalau None (S/R blm ada), JANGAN timpa target_price dgn None
            elif self.target_category in computed:
                self.target_price = computed[self.target_category]
        elif not self.target_category:
            # Default ke Moderate kalau belum dipilih sama sekali
            self.target_category = "Moderate (2.5R)"
            self.target_price = computed["Moderate (2.5R)"]

    def check_risk_management_rules(self):
        """Check all risk management guard rails before allowing new trade."""
        settings = frappe.get_single("Trading Account Settings")

        self.check_daily_loss_limit(settings)
        self.check_consecutive_losses(settings)
        self.check_per_stock_exposure(settings)
        self.check_total_exposure(settings)

    def check_daily_loss_limit(self, settings):
        """Block new trade if daily loss limit is breached."""
        today = frappe.utils.today()
        daily_loss_limit = settings.modal_total * (settings.daily_loss_limit_percent / 100)

        result = frappe.db.sql(
            """
            SELECT SUM(result_rp) as total_loss
            FROM `tabTrade Journal`
            WHERE date = %s AND status = 'Closed' AND result_rp < 0
            """,
            (today,),
            as_dict=True
        )

        total_loss = result[0].total_loss if result and result[0].total_loss else 0

        if total_loss and total_loss <= -daily_loss_limit:
            frappe.throw(
                _("Daily loss limit breached. Total loss today: {0}. Stop trading per your rules.").format(
                    frappe.format_value(total_loss, {"fieldtype": "Currency"})
                )
            )

    def check_consecutive_losses(self, settings):
        """Block new trade if max consecutive losses reached."""
        max_losses = settings.max_consecutive_losses

        recent_trades = frappe.db.get_list(
            "Trade Journal",
            filters={"status": "Closed"},
            fields=["result_r"],
            order_by="date DESC",
            limit=max_losses
        )

        if len(recent_trades) >= max_losses:
            all_losses = all(trade.result_r < 0 for trade in recent_trades if trade.result_r is not None)
            if all_losses:
                frappe.throw(
                    _("{0} consecutive losses detected. Stop trading today per your rules.").format(max_losses)
                )

    def check_per_stock_exposure(self, settings):
        """Block new trade if per-stock exposure limit is exceeded."""
        max_per_stock = settings.modal_total * (settings.max_per_stock_percent / 100)

        result = frappe.db.sql(
            """
            SELECT SUM(entry_price * position_lot * 100) as total_value
            FROM `tabTrade Journal`
            WHERE ticker = %s AND status = 'Open'
            """,
            (self.ticker,),
            as_dict=True
        )

        current_value = result[0].total_value if result and result[0].total_value else 0
        new_position_value = self.entry_price * self.position_lot * 100 if self.position_lot else 0
        total_after_new = current_value + new_position_value

        if total_after_new > max_per_stock:
            frappe.throw(
                _("Per-stock exposure limit exceeded. Current: {0}, New: {1}, Limit: {2}").format(
                    frappe.format_value(current_value, {"fieldtype": "Currency"}),
                    frappe.format_value(new_position_value, {"fieldtype": "Currency"}),
                    frappe.format_value(max_per_stock, {"fieldtype": "Currency"})
                )
            )

    def check_total_exposure(self, settings):
        """Block new trade if total portfolio exposure limit is exceeded."""
        max_exposure = settings.modal_total * (settings.max_exposure_percent / 100)

        result = frappe.db.sql(
            """
            SELECT SUM(entry_price * position_lot * 100) as total_value
            FROM `tabTrade Journal`
            WHERE status = 'Open'
            """,
            as_dict=True
        )

        current_total = result[0].total_value if result and result[0].total_value else 0
        new_position_value = self.entry_price * self.position_lot * 100 if self.position_lot else 0
        total_after_new = current_total + new_position_value

        if total_after_new > max_exposure:
            frappe.throw(
                _("Total portfolio exposure limit exceeded. Current: {0}, New: {1}, Limit: {2}").format(
                    frappe.format_value(current_total, {"fieldtype": "Currency"}),
                    frappe.format_value(new_position_value, {"fieldtype": "Currency"}),
                    frappe.format_value(max_exposure, {"fieldtype": "Currency"})
                )
            )

    def on_update(self):
        """Trigger Telegram notification hanya saat transisi ke Closed,
        bukan di setiap save berikutnya selama status masih Closed."""
        if (self.status == "Closed" and self.exit_price and self.result_r is not None
                and self.has_value_changed("status")):
            notify_on_close(self)

        # Compounding otomatis (22 Sep 2026): sekali trade Closed & result_rp
        # sudah terhitung, tambahkan ke modal_total Trading Account Settings.
        # TIDAK digabung dgn kondisi has_value_changed("status") di atas --
        # sengaja dicek independen lewat flag capital_applied sendiri, supaya
        # tetap idempotent walau BUG #1 (dobel on_update) kambuh lagi nanti.
        if self.status == "Closed" and self.result_rp is not None and not self.capital_applied:
            self._auto_apply_capital_change()
        elif self.capital_applied and self.status != "Closed" and self.has_value_changed("status"):
            # Batal-close (22 Sep 2026): status dibalik dari Closed ke status
            # lain SETELAH modal sempat ter-update -- kembalikan modal.
            self._reverse_capital_change()


    def _auto_apply_capital_change(self):
        """Compounding otomatis: tambahkan result_rp trade ini ke modal_total
        (BUKAN modal_awal -- modal_awal statis, cuma catatan deposit).
        Pakai db_set (bukan .save() lagi) supaya TIDAK memicu validate()/
        on_update() berulang -- mencegah rekursi & dobel-tambah. Fail-silent:
        kalau gagal (mis. Trading Account Settings belum pernah disimpan),
        log error saja -- trade tetap tersimpan, modal bisa dikoreksi manual.

        CATATAN DESAIN (disepakati 22 Sep 2026): kalau exit_price diedit
        SETELAH capital_applied=1, modal_total TIDAK ikut terkoreksi otomatis
        (mirip settlement broker yang final). Koreksi salah input dilakukan
        manual di Trading Account Settings."""
        try:
            settings = frappe.get_single("Trading Account Settings")
            settings.modal_total = (settings.modal_total or 0) + self.result_rp
            settings.save(ignore_permissions=True)
            self.db_set("capital_applied", 1, update_modified=False)
            self.db_set("capital_applied_amount", self.result_rp, update_modified=False)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Auto-apply capital change gagal untuk {self.name}"
            )

    def _reverse_capital_change(self):
        """Undo compounding kalau status Closed dibatalkan (balik ke Open/
        lainnya) SETELAH modal sempat ter-update. Pakai capital_applied_amount
        (BUKAN result_rp saat ini) -- angka yang dikembalikan PERSIS sama
        dengan yang sempat ditambahkan, aman walau result_rp sudah berubah
        duluan (mis. exit_price ikut diedit di save yang sama)."""
        try:
            settings = frappe.get_single("Trading Account Settings")
            settings.modal_total = (settings.modal_total or 0) - (self.capital_applied_amount or 0)
            settings.save(ignore_permissions=True)
            self.db_set("capital_applied", 0, update_modified=False)
            self.db_set("capital_applied_amount", 0, update_modified=False)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Reverse capital change gagal untuk {self.name}"
            )


def notify_on_close(doc, method=None):
    """Send Telegram notification when a trade is closed."""
    from fd_trade.utils.telegram import send_telegram_notification

    followed_status = "Yes" if doc.followed_system else "No"
    # BUG #3 FIX (17 Sep 2026): sebelumnya pakai "\\n" (backslash literal + n
    # sebagai teks, bukan newline asli), jadi tampil satu baris panjang di
    # Telegram. Diganti f-string dengan "\n" asli, konsisten dengan pola
    # yang sudah benar di tasks.py (daily_review_notification, dst).
    message = (
        f"Trade Closed\n"
        f"Ticker: {doc.ticker}\n"
        f"Result R: {doc.result_r}R\n"
        f"Followed System: {followed_status}"
    )

    send_telegram_notification(message)


@frappe.whitelist()
def fetch_support_resistance(docname):
    """Ambil & simpan level Support/Resistance untuk Trade Journal tertentu."""
    from fd_trade.utils.price_data import get_support_resistance

    doc = frappe.get_doc("Trade Journal", docname)
    result = get_support_resistance(doc.ticker)

    if not result:
        frappe.throw(_("Gagal mengambil data Support/Resistance untuk ticker {0}. Cek nama ticker atau koneksi.").format(doc.ticker))

    doc.support_level = result["support_level"]
    doc.support_level_2 = result["support_level_2"]
    doc.support_level_3 = result["support_level_3"]
    doc.resistance_level = result["resistance_level"]
    doc.resistance_level_2 = result["resistance_level_2"]
    doc.resistance_level_3 = result["resistance_level_3"]
    doc.sr_details = result["details"]
    doc.save()

    return result


@frappe.whitelist()
def close_position(docname: str, exit_price: float):
    """Tutup posisi dari tombol 'Close Position' di List View -- set
    exit_price + status Closed, lalu .save() memicu calculate_risk_metrics()
    (hitung result_rp/result_r) dan on_update() (notify Telegram + compounding
    modal_total). Return result_rp untuk ditampilkan JS (frappe.show_alert).

    BUG FIX (22 Sep 2026): parameter dari frappe.call() datang sebagai string
    lewat HTTP walau JS mengirim angka murni. Type hint ": float" di signature
    memicu Frappe's typing_validations wrapper utk auto-cast -- tapi sebagai
    lapis pengaman kedua, tetap cast eksplisit float() di sini (defense in
    depth, jangan cuma andalkan wrapper framework)."""
    doc = frappe.get_doc("Trade Journal", docname)

    if doc.status == "Closed":
        frappe.throw(_("Trade {0} sudah berstatus Closed.").format(docname))

    doc.exit_price = float(exit_price)
    doc.status = "Closed"
    doc.save()

    return {"result_rp": doc.result_rp}
