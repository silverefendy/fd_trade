"""
Installation hooks for FD-Trade app.
Called by before_install / after_install in hooks.py
"""

import frappe


def before_install():
    """Runs before app installation. Currently no-op."""
    pass


def after_install():
    """BUG #4 FIX (17 Sep 2026): auto-create default Trading Account Settings
    kalau belum pernah disimpan, supaya Trade Journal pertama tidak crash
    saat calculate_risk_metrics() memanggil frappe.get_single() dan
    field seperti modal_total masih kosong/tidak konsisten.

    Nilai default di bawah SENGAJA konservatif -- user WAJIB membuka dan
    menyesuaikan Modal Total & limit risiko sesuai kondisi riil sebelum
    mulai trading serius. Ini cuma jaring pengaman supaya tidak crash,
    BUKAN pengganti pengisian manual yang sudah didokumentasikan di
    docs/01_GUIDE.md bagian Setup Awal.
    """
    if frappe.db.exists("Trading Account Settings", "Trading Account Settings"):
        return

    settings = frappe.get_single("Trading Account Settings")
    settings.modal_total = settings.modal_total or 0
    settings.risk_per_trade_percent = settings.risk_per_trade_percent or 0.5
    settings.daily_loss_limit_percent = settings.daily_loss_limit_percent or 2
    settings.weekly_loss_limit_percent = settings.weekly_loss_limit_percent or 5
    settings.monthly_circuit_breaker_percent = settings.monthly_circuit_breaker_percent or 10
    settings.max_exposure_percent = settings.max_exposure_percent or 60
    settings.max_per_stock_percent = settings.max_per_stock_percent or 20
    settings.max_consecutive_losses = settings.max_consecutive_losses or 3
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.logger().info("FD-Trade: Trading Account Settings default berhasil dibuat via after_install().")
