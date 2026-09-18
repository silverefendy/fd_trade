import json
import os
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase


class FDTradeTestCase(FrappeTestCase):
    """Base test FD-Trade dengan default settings yang tersimpan."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings = frappe.get_single("Trading Account Settings")
        defaults = {
            "modal_total": 30_000_000,
            "risk_per_trade_percent": 0.5,
            "max_per_stock_percent": 15,
            "max_exposure_percent": 60,
            "daily_loss_limit_percent": 1,
            "weekly_loss_limit_percent": 3,
            "monthly_circuit_breaker_percent": 5,
            "max_consecutive_losses": 3,
            "proximity_threshold_pct": 3,
            "volume_high_ratio": 1.5,
            "volume_low_ratio": 0.5,
            "ihsg_signal_retention_days": 90,
        }
        changed = False
        for field, value in defaults.items():
            if getattr(settings, field, None) is None:
                setattr(settings, field, value)
                changed = True
        if changed or not frappe.db.exists("Trading Account Settings"):
            settings.save(ignore_permissions=True)
        frappe.db.commit()

    @staticmethod
    def json_doctype(doctype):
        filename = frappe.scrub(doctype)
        path = Path(__file__).parents[1] / "doctype" / filename / f"{filename}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def select_options(cls, doctype, fieldname):
        for field in cls.json_doctype(doctype)["fields"]:
            if field.get("fieldname") == fieldname:
                return [line for line in field.get("options", "").splitlines() if line]
        raise AssertionError(f"Field {fieldname} tidak ditemukan di {doctype}")

    @staticmethod
    def live_mode():
        return os.getenv("FD_TRADE_TEST_LIVE", "0") == "1"
