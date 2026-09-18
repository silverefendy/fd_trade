"""
Trade Journal Controller
Core logging doctype for trading entries with risk management validation
dan perhitungan target price otomatis berbasis R-multiple.
"""

import frappe
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

    def validate(self):
        """Validate trade entry and calculate risk metrics."""
        if self.ticker:
            self.ticker = self.ticker.strip().upper()
        self.calculate_risk_metrics()

        if self.is_new() or self.has_value_changed("ticker"):
            self._auto_fetch_support_resistance()

        if self.is_new():
            self.check_risk_management_rules()

    def _auto_fetch_support_resistance(self):
        """Ambil Support/Resistance otomatis dari yfinance saat ticker baru
        diisi atau diganti, fail-silent (tidak menghentikan proses save
        kalau yfinance gagal/timeout)."""
        if not self.ticker:
            return

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

        self.target_suggestions = "\n".join(suggestion_lines)

        # Kalau kategori bukan Custom, auto-isi target_price.
        # Kalau Custom, biarkan nilai yang sudah diinput user (tidak ditimpa).
        if self.target_category and self.target_category != "Custom":
            if self.target_category in computed:
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
        """Trigger Telegram notification when trade is closed."""
        if self.status == "Closed" and self.exit_price and self.result_r is not None:
            notify_on_close(self)


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
