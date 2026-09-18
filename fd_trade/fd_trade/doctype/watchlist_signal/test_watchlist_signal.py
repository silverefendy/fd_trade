# Copyright (c) 2026, Efendy (silverefendy) and Contributors
# See license.txt

from inspect import signature
from unittest.mock import patch

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

	def test_recommendation_change_message_is_telegram_safe(self):
		message = _build_recommendation_change_message("TLKM", "Wait", "Sell", 3000, notes="Dekat resistance")
		self.assertIn("TLKM", message)
		self.assertIn("Rp3,000", message)

	@patch("fd_trade.utils.telegram.send_telegram_notification")
	@patch("fd_trade.utils.price_data.get_volume_confirmation", return_value=None)
	@patch("fd_trade.utils.price_data.get_pivot_points", return_value=None)
	@patch("fd_trade.utils.price_data.calculate_recommendation", return_value={"recommendation": "Buy", "recommendation_price_low": 100, "recommendation_price_high": 101, "stop_loss": 95})
	def test_create_signal_notifies_only_on_change(self, calculate, pivot, volume, telegram):
		import frappe
		from fd_trade.fd_trade.doctype.watchlist_signal import watchlist_signal
		settings = frappe._dict({"proximity_threshold_pct": 3, "volume_high_ratio": 1.5, "volume_low_ratio": 0.5, "ihsg_trend": "Sideways"})
		signal_doc = frappe._dict({"insert": lambda ignore_permissions=True: None})
		calculate.side_effect = [
			{"recommendation": "Buy", "recommendation_price_low": 100, "recommendation_price_high": 101, "stop_loss": 95},
			{"recommendation": "Sell", "recommendation_price_low": 110, "recommendation_price_high": 110},
		]
		with patch.object(frappe, "get_single", return_value=settings), \
			patch.object(frappe, "get_all", side_effect=[[], [], [], [frappe._dict({"recommendation": "Buy"})]]), \
			patch.object(frappe, "get_doc", return_value=signal_doc), \
			patch.object(frappe.db, "commit"), \
			patch.object(frappe, "log_error"):
			watchlist_signal.create_signal("WL-BBCA", "BBCA", 101, "Bullish Lemah", 100, None, 110)
			watchlist_signal.create_signal("WL-BBCA", "BBCA", 109, "Sideways", 100, None, 110)
		telegram.assert_called_once()
		self.assertIn("BBCA Buy -> Sell", telegram.call_args.args[0])
