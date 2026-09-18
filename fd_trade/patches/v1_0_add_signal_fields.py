"""Patch untuk memastikan schema field baru tersedia pada site existing."""

import frappe


def execute():
    """Reload DocType JSON agar field tambahan tersinkron saat migrate."""
    for doctype in ("Watchlist", "Trade Journal", "Trading Account Settings", "Watchlist Signal"):
        module = frappe.db.get_value("DocType", doctype, "module") or "FD-Trade"
        frappe.reload_doc(module, "doctype", frappe.scrub(doctype))
