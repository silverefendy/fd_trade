"""
Watchlist Controller
Manages stock watchlist with tier classification.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now


class Watchlist(Document):
"""Watchlist entry for tracking potential trading opportunities."""

def before_save(self):
"""Update last_updated timestamp before saving."""
self.last_updated = now()
