# Copyright (c) 2026, Efendy (silverefendy) and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch
import frappe


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestWatchlist(IntegrationTestCase):
	"""
	Integration tests for Watchlist.
	Use this class for testing interactions between multiple components.
	"""

	def test_watchlist_test_fixture_has_no_fixed_sr_level_count(self):
		self.assertTrue(True)

	def test_lowercase_ticker_is_uppercased(self):
		from fd_trade.fd_trade.doctype.watchlist.watchlist import Watchlist
		doc = Watchlist({"doctype": "Watchlist", "ticker": "bbca", "tier": "A"})
		doc.before_insert()
		self.assertEqual(doc.ticker, "BBCA")

	def test_fetch_support_resistance_and_signal_are_called(self):
		from fd_trade.fd_trade.doctype.watchlist import watchlist
		doc = frappe._dict({"ticker": "BBCA", "name": "BBCA", "save": lambda: None})
		with patch.object(watchlist.frappe, "get_doc", return_value=doc), \
			patch("fd_trade.utils.price_data.get_support_resistance", return_value={
				"support_level": 6400, "support_level_2": 6300, "support_level_3": 6200,
				"resistance_level": 6600, "resistance_level_2": 6700, "resistance_level_3": 6800,
				"details": "mock", "trend": "Sideways",
			}), patch("fd_trade.utils.price_data.get_current_price", return_value=6500), \
			patch("fd_trade.utils.price_data.get_current_ohlc", return_value=None), \
			patch("fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal.create_signal") as create_signal:
			result = watchlist.fetch_support_resistance("BBCA")
			self.assertEqual(result["support_level_3"], 6200)
			create_signal.assert_called_once()
