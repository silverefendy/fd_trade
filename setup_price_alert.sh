#!/bin/bash
###############################################################################
# FD-Trade: Setup Price Alert DocType + Target Price Otomatis
# Site: trace.ciptamebel.co.id
#
# CARA PAKAI:
#   1. Copy script ini ke home directory bench Anda (folder yang berisi apps/, sites/)
#   2. chmod +x setup_price_alert.sh
#   3. ./setup_price_alert.sh
#   4. Ikuti instruksi di akhir script untuk migrate & restart
#
# Script ini akan:
#   - Membuat DocType baru "Price Alert"
#   - Menimpa (overwrite) trade_journal.py dengan versi baru (target price otomatis)
#   - Menimpa trade_journal.json (tambah field target_category & target_suggestions)
#   - Menambah fungsi check_price_alerts() ke tasks.py
#   - Menimpa hooks.py (tambah scheduler entry baru)
###############################################################################

set -e

APP_DIR="apps/fd_trade/fd_trade/fd_trade"
SITE="trace.ciptamebel.co.id"

if [ ! -d "apps/fd_trade" ]; then
    echo "ERROR: Jalankan script ini dari root folder bench (yang berisi folder apps/ dan sites/)."
    echo "Contoh: cd /home/frappe/frappe-bench && bash setup_price_alert.sh"
    exit 1
fi

echo "==> Membuat folder DocType Price Alert..."
mkdir -p "$APP_DIR/doctype/price_alert"

###############################################################################
# 1. Price Alert - __init__.py
###############################################################################
cat > "$APP_DIR/doctype/price_alert/__init__.py" << 'EOF'
EOF

###############################################################################
# 2. Price Alert - price_alert.json
###############################################################################
cat > "$APP_DIR/doctype/price_alert/price_alert.json" << 'EOF'
{
 "actions": [],
 "allow_import": 1,
 "allow_rename": 0,
 "creation": "2026-09-14 16:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "linked_trade",
  "ticker",
  "alert_type",
  "column_break_1",
  "trigger_price",
  "condition",
  "status",
  "section_break_1",
  "notes",
  "triggered_at"
 ],
 "fields": [
  {
   "fieldname": "linked_trade",
   "fieldtype": "Link",
   "label": "Trade Journal",
   "options": "Trade Journal",
   "reqd": 1,
   "in_list_view": 1
  },
  {
   "fieldname": "ticker",
   "fieldtype": "Data",
   "label": "Ticker",
   "fetch_from": "linked_trade.ticker",
   "fetch_if_empty": 1,
   "in_list_view": 1,
   "reqd": 1
  },
  {
   "fieldname": "alert_type",
   "fieldtype": "Select",
   "label": "Alert Type",
   "options": "Take Profit\nStop Loss\nBuy Trigger\nCustom",
   "reqd": 1,
   "in_list_view": 1
  },
  {
   "fieldname": "column_break_1",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "trigger_price",
   "fieldtype": "Currency",
   "label": "Trigger Price",
   "reqd": 1,
   "in_list_view": 1
  },
  {
   "fieldname": "condition",
   "fieldtype": "Select",
   "label": "Condition",
   "options": ">=\n<=",
   "reqd": 1,
   "description": ">= artinya alert aktif saat harga NAIK mencapai/melewati trigger. <= artinya saat harga TURUN mencapai/melewati trigger."
  },
  {
   "fieldname": "status",
   "fieldtype": "Select",
   "label": "Status",
   "options": "Active\nTriggered\nCancelled",
   "default": "Active",
   "in_list_view": 1
  },
  {
   "fieldname": "section_break_1",
   "fieldtype": "Section Break",
   "label": "Detail"
  },
  {
   "fieldname": "notes",
   "fieldtype": "Small Text",
   "label": "Notes"
  },
  {
   "fieldname": "triggered_at",
   "fieldtype": "Datetime",
   "label": "Triggered At",
   "read_only": 1
  }
 ],
 "index_web_pages_for_search": 1,
 "links": [],
 "modified": "2026-09-14 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "FD-Trade",
 "name": "Price Alert",
 "owner": "Administrator",
 "permissions": [
  {
   "create": 1,
   "delete": 1,
   "email": 1,
   "print": 1,
   "read": 1,
   "role": "System Manager",
   "share": 1,
   "write": 1
  },
  {
   "create": 1,
   "email": 1,
   "print": 1,
   "read": 1,
   "role": "All",
   "share": 1,
   "write": 1
  }
 ],
 "quick_entry": 1,
 "sort_field": "modified",
 "sort_order": "DESC",
 "track_changes": 1
}
EOF

###############################################################################
# 3. Price Alert - price_alert.py
###############################################################################
cat > "$APP_DIR/doctype/price_alert/price_alert.py" << 'EOF'
"""
Price Alert Controller
Alert untuk harga tertentu (TP/SL/Buy Trigger) yang selalu terikat ke Trade Journal,
baik untuk posisi yang sudah open maupun rencana yang belum entry.
"""

import frappe
from frappe.model.document import Document


class PriceAlert(Document):
    """Price Alert entry - dicek berkala oleh scheduled job check_price_alerts()."""

    def validate(self):
        """Pastikan ticker terisi dari linked_trade jika kosong, dan
        set default condition berdasarkan alert_type jika belum diisi."""
        if not self.ticker and self.linked_trade:
            self.ticker = frappe.db.get_value("Trade Journal", self.linked_trade, "ticker")

        if not self.condition:
            if self.alert_type in ("Take Profit", "Buy Trigger"):
                self.condition = ">="
            elif self.alert_type == "Stop Loss":
                self.condition = "<="
EOF

echo "==> Price Alert DocType selesai dibuat."

###############################################################################
# 4. Overwrite trade_journal.json - tambah target_category & target_suggestions
###############################################################################
echo "==> Update trade_journal.json (menambah field target_category & target_suggestions)..."

cat > "$APP_DIR/doctype/trade_journal/trade_journal.json" << 'EOF'
{
 "actions": [],
 "allow_import": 1,
 "allow_rename": 1,
 "creation": "2026-09-14 14:59:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "basic_info_section",
  "date",
  "ticker",
  "setup",
  "market_regime",
  "entry_section",
  "entry_price",
  "stop_loss",
  "target_category",
  "target_price",
  "target_suggestions",
  "position_lot",
  "suggested_lot",
  "risk_amount",
  "risk_r",
  "exit_section",
  "exit_price",
  "result_r",
  "result_rp",
  "status",
  "psychology_section",
  "followed_system",
  "fomo",
  "revenge",
  "emotion",
  "mistake",
  "lesson",
  "attachments_section",
  "screenshot_before",
  "screenshot_after",
  "signal_source_ref"
 ],
 "fields": [
  {
   "fieldname": "basic_info_section",
   "fieldtype": "Section Break",
   "label": "Basic Information"
  },
  {
   "fieldname": "date",
   "fieldtype": "Date",
   "label": "Date",
   "reqd": 1
  },
  {
   "fieldname": "ticker",
   "fieldtype": "Data",
   "label": "Ticker",
   "reqd": 1
  },
  {
   "fieldname": "setup",
   "fieldtype": "Select",
   "label": "Setup",
   "options": "Breakout\nPullback\nOther"
  },
  {
   "fieldname": "market_regime",
   "fieldtype": "Select",
   "label": "Market Regime",
   "options": "Bull\nSideways\nBear"
  },
  {
   "fieldname": "entry_section",
   "fieldtype": "Section Break",
   "label": "Entry & Risk Management"
  },
  {
   "fieldname": "entry_price",
   "fieldtype": "Currency",
   "label": "Entry Price",
   "reqd": 1
  },
  {
   "fieldname": "stop_loss",
   "fieldtype": "Currency",
   "label": "Stop Loss",
   "reqd": 1
  },
  {
   "fieldname": "target_category",
   "fieldtype": "Select",
   "label": "Target Category",
   "options": "Conservative (1.5R)\nModerate (2.5R)\nAggressive (4R)\nCustom",
   "default": "Moderate (2.5R)",
   "description": "Pilih kategori target profit berbasis R-multiple. Pilih 'Custom' untuk isi Target Price manual."
  },
  {
   "fieldname": "target_price",
   "fieldtype": "Currency",
   "label": "Target Price",
   "description": "Otomatis terisi berdasarkan Target Category, kecuali dipilih 'Custom'."
  },
  {
   "fieldname": "target_suggestions",
   "fieldtype": "Small Text",
   "label": "Target Suggestions (Auto)",
   "read_only": 1,
   "description": "Perhitungan otomatis 3 skenario target berdasarkan jarak Entry Price ke Stop Loss."
  },
  {
   "fieldname": "position_lot",
   "fieldtype": "Int",
   "label": "Position Lot"
  },
  {
   "fieldname": "suggested_lot",
   "fieldtype": "Int",
   "label": "Suggested Lot",
   "read_only": 1
  },
  {
   "fieldname": "risk_amount",
   "fieldtype": "Currency",
   "label": "Risk Amount",
   "read_only": 1
  },
  {
   "fieldname": "risk_r",
   "fieldtype": "Float",
   "label": "Risk R",
   "read_only": 1,
   "default": "1.0"
  },
  {
   "fieldname": "exit_section",
   "fieldtype": "Section Break",
   "label": "Exit & Results"
  },
  {
   "fieldname": "exit_price",
   "fieldtype": "Currency",
   "label": "Exit Price"
  },
  {
   "fieldname": "result_r",
   "fieldtype": "Float",
   "label": "Result R"
  },
  {
   "fieldname": "result_rp",
   "fieldtype": "Currency",
   "label": "Result Rp",
   "read_only": 1
  },
  {
   "fieldname": "status",
   "fieldtype": "Select",
   "label": "Status",
   "options": "Open\nClosed",
   "default": "Open"
  },
  {
   "fieldname": "psychology_section",
   "fieldtype": "Section Break",
   "label": "Psychology & Learning"
  },
  {
   "fieldname": "followed_system",
   "fieldtype": "Check",
   "label": "Followed System"
  },
  {
   "fieldname": "fomo",
   "fieldtype": "Check",
   "label": "FOMO"
  },
  {
   "fieldname": "revenge",
   "fieldtype": "Check",
   "label": "Revenge"
  },
  {
   "fieldname": "emotion",
   "fieldtype": "Small Text",
   "label": "Emotion"
  },
  {
   "fieldname": "mistake",
   "fieldtype": "Small Text",
   "label": "Mistake"
  },
  {
   "fieldname": "lesson",
   "fieldtype": "Text",
   "label": "Lesson"
  },
  {
   "fieldname": "attachments_section",
   "fieldtype": "Section Break",
   "label": "Attachments"
  },
  {
   "fieldname": "screenshot_before",
   "fieldtype": "Attach Image",
   "label": "Screenshot Before"
  },
  {
   "fieldname": "screenshot_after",
   "fieldtype": "Attach Image",
   "label": "Screenshot After"
  },
  {
   "fieldname": "signal_source_ref",
   "fieldtype": "Link",
   "label": "Signal Source",
   "options": "Signal Source"
  }
 ],
 "index_web_pages_for_search": 1,
 "links": [],
 "modified": "2026-09-14 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "FD-Trade",
 "name": "Trade Journal",
 "owner": "Administrator",
 "permissions": [
  {
   "create": 1,
   "delete": 1,
   "email": 1,
   "print": 1,
   "read": 1,
   "role": "System Manager",
   "share": 1,
   "write": 1
  },
  {
   "create": 1,
   "email": 1,
   "print": 1,
   "read": 1,
   "role": "All",
   "share": 1,
   "write": 1
  }
 ],
 "quick_entry": 1,
 "sort_field": "modified",
 "sort_order": "DESC",
 "track_changes": 1
}
EOF

###############################################################################
# 5. Overwrite trade_journal.py - tambah logic target price otomatis
###############################################################################
echo "==> Update trade_journal.py (logic target price otomatis + suggestion)..."

cat > "$APP_DIR/doctype/trade_journal/trade_journal.py" << 'EOF'
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
        self.calculate_risk_metrics()

        if self.is_new():
            self.check_risk_management_rules()

    def calculate_risk_metrics(self):
        """Calculate risk amount, suggested lot, target price suggestions,
        dan validasi stop loss."""
        settings = frappe.get_single("Trading Account Settings")

        # Calculate risk per share
        risk_per_share = self.entry_price - self.stop_loss

        if risk_per_share <= 0:
            frappe.throw(_("Stop loss must be below entry price for long positions."))

        # Calculate risk amount in rupiah
        risk_rp = settings.modal_total * (settings.risk_per_trade_percent / 100)
        self.risk_amount = risk_rp

        # Calculate suggested lot (rounded down to nearest 100 shares)
        suggested_shares = int(risk_rp / risk_per_share)
        self.suggested_lot = int(suggested_shares / 100)

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

        todays_losses = frappe.db.get_list(
            "Trade Journal",
            filters={
                "date": today,
                "status": "Closed",
                "result_rp": ["<", 0]
            },
            fields=["SUM(result_rp) as total_loss"]
        )

        if todays_losses and todays_losses[0].total_loss:
            if todays_losses[0].total_loss <= -daily_loss_limit:
                frappe.throw(
                    _("Daily loss limit breached. Total loss today: {0}. Stop trading per your rules.").format(
                        frappe.format_value(todays_losses[0].total_loss, {"fieldtype": "Currency"})
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

        current_exposure = frappe.db.get_list(
            "Trade Journal",
            filters={
                "ticker": self.ticker,
                "status": "Open"
            },
            fields=["SUM(entry_price * position_lot * 100) as total_value"]
        )

        current_value = current_exposure[0].total_value if current_exposure and current_exposure[0].total_value else 0
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

        total_exposure = frappe.db.get_list(
            "Trade Journal",
            filters={"status": "Open"},
            fields=["SUM(entry_price * position_lot * 100) as total_value"]
        )

        current_total = total_exposure[0].total_value if total_exposure and total_exposure[0].total_value else 0
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
    message = "Trade Closed\\nTicker: " + doc.ticker + "\\nResult R: " + str(doc.result_r) + "R\\nFollowed System: " + followed_status

    send_telegram_notification(message)
EOF

###############################################################################
# 6. Tambah fungsi check_price_alerts() ke tasks.py
###############################################################################
echo "==> Menambah fungsi check_price_alerts ke tasks.py..."

cat >> "apps/fd_trade/fd_trade/tasks.py" << 'EOF'


def check_price_alerts():
    """Cek semua Price Alert dengan status Active, bandingkan dengan harga
    current (via yfinance, delay 15-20 menit), kirim notifikasi Telegram
    jika kondisi trigger terpenuhi.

    Berjalan setiap 15 menit selama jam bursa (9-16, Senin-Jumat).
    """
    from fd_trade.utils.price_data import get_current_price
    from fd_trade.utils.telegram import send_telegram_notification

    try:
        active_alerts = frappe.get_all(
            "Price Alert",
            filters={"status": "Active"},
            fields=["name", "ticker", "alert_type", "trigger_price", "condition", "linked_trade"]
        )

        for alert in active_alerts:
            current_price = get_current_price(alert.ticker)

            if current_price is None:
                # Gagal ambil harga (network/ticker salah), skip, jangan crash job.
                continue

            triggered = False
            if alert.condition == ">=" and current_price >= alert.trigger_price:
                triggered = True
            elif alert.condition == "<=" and current_price <= alert.trigger_price:
                triggered = True

            if triggered:
                message = (
                    f"\U0001F514 PRICE ALERT: {alert.ticker}\n"
                    f"Type: {alert.alert_type}\n"
                    f"Trigger: Rp{alert.trigger_price:,.0f} | Current: Rp{current_price:,.0f}\n"
                    f"Linked Trade: {alert.linked_trade}\n"
                    f"(Catatan: harga yfinance delay 15-20 menit, konfirmasi manual sebelum eksekusi)"
                )
                send_telegram_notification(message)

                frappe.db.set_value("Price Alert", alert.name, {
                    "status": "Triggered",
                    "triggered_at": frappe.utils.now()
                })
                frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"check_price_alerts failed: {e}", "FD-Trade Scheduled Tasks")
EOF

###############################################################################
# 7. Overwrite hooks.py - tambah scheduler entry check_price_alerts
###############################################################################
echo "==> Update hooks.py (tambah scheduler entry check_price_alerts, tiap 15 menit)..."

cat > "apps/fd_trade/fd_trade/hooks.py" << 'EOF'
"""
FD-Trade App Hooks
Defines integration points with Frappe framework.
"""

app_name = "fd_trade"
app_title = "FD-Trade"
app_publisher = "Efendy (silverefendy)"
app_description = "Personal stock trading journal, risk management, and broker-flow screening system for Indonesian stock market (IDX) swing and fast trading."
app_icon = "octicon octicon-graph"
app_color = "grey"
app_email = "silverefendy@users.noreply.github.com"
app_license = "MIT"

# Includes in JS
# include_js = []

# Includes in CSS
# include_css = []

# Home Page
# home_page = "dashboard"

# Website Generators
# website_generators = []

# Installation
before_install = "fd_trade.install.before_install"
after_install = "fd_trade.install.after_install"

# Scheduler Events
scheduler_events = {
    "cron": {
        "*/30 9-16 * * 1-5": [
            "fd_trade.tasks.check_intraday_conditions"
        ],
        "*/15 9-16 * * 1-5": [
            "fd_trade.tasks.check_price_alerts"
        ],
        "0 16 * * 1-5": [
            "fd_trade.tasks.daily_review_notification"
        ],
        "0 17 * * 5": [
            "fd_trade.tasks.weekly_review_notification"
        ],
        "0 8 1 * *": [
            "fd_trade.tasks.monthly_circuit_breaker_check"
        ],
    }
}

# Doc Events
doc_events = {
    "Trade Journal": {
        "on_update": "fd_trade.fd_trade.doctype.trade_journal.trade_journal.notify_on_close"
    }
}

# Permissions
# permission_query_conditions = {}

# Document Events
# doc_events = {}

# Notification Config
# notification_config = ""

# Web Templates
# web_templates = {}

# Standard Queries
# standard_queries = {}

# Jinja Context
# jinja_context = {}

# Extensions
# extensions = {}

IGNORED_FILES = ["*.pyc", "*.pyo", "__pycache__"]
EOF

echo ""
echo "=============================================================="
echo "SEMUA FILE SELESAI DIBUAT."
echo "=============================================================="
echo ""
echo "LANGKAH SELANJUTNYA (jalankan manual):"
echo ""
echo "  bench --site $SITE migrate"
echo "  bench build"
echo "  bench restart"
echo ""
echo "Setelah itu:"
echo "  1. Buka DocType 'Price Alert' di UI -> pastikan muncul di list DocType"
echo "  2. Buka Trade Journal -> cek field baru: Target Category, Target Price, Target Suggestions"
echo "  3. Buat 1 Trade Journal baru (boleh position_lot = 0 dulu kalau belum entry)"
echo "     -> isi entry_price & stop_loss -> lihat target_suggestions otomatis muncul"
echo "  4. Buat Price Alert baru, link ke Trade Journal tersebut"
echo "  5. Tunggu siklus scheduler 15 menit berikutnya (jam bursa), atau test manual via console:"
echo ""
echo "     bench --site $SITE console"
echo "     >>> from fd_trade.tasks import check_price_alerts"
echo "     >>> check_price_alerts()"
echo ""
echo "=============================================================="
