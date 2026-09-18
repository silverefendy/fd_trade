# Copyright (c) 2026, Efendy (silverefendy) and Contributors
# See license.txt

from inspect import signature

from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import (
	_build_recommendation_change_message,
	create_signal,
)
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestWatchlistSignal(IntegrationTestCase):
	"""
	Integration tests for WatchlistSignal.
	Use this class for testing interactions between multiple components.
	"""

	def test_create_signal_accepts_three_level_arguments(self):
		parameters = signature(create_signal).parameters
		self.assertIn("support_level_3", parameters)
		self.assertIn("resistance_level_2", parameters)
		self.assertIn("resistance_level_3", parameters)

	def test_new_ticker_does_not_notify(self):
		self.assertIsNone(_build_recommendation_change_message("BBCA", None, "Buy", 100))

	def test_same_recommendation_does_not_notify(self):
		self.assertIsNone(_build_recommendation_change_message("BBCA", "Buy", "Buy", 100))

	def test_changed_buy_recommendation_message(self):
		message = _build_recommendation_change_message(
			"BBCA", "Wait", "Buy", 101, 100, 101, 95,
		)
		self.assertIn("Sinyal berubah: BBCA Wait -> Buy @ Rp101", message)
		self.assertIn("Entry zone: Rp100 - Rp101", message)
		self.assertIn("Stop loss: Rp95", message)

	def test_changed_sell_recommendation_includes_reason(self):
		message = _build_recommendation_change_message(
			"BBCA", "Buy", "Sell", 110, notes="Mendekati resistance."
		)
		self.assertIn("Sinyal berubah: BBCA Buy -> Sell @ Rp110", message)
		self.assertIn("Alasan: Mendekati resistance.", message)
