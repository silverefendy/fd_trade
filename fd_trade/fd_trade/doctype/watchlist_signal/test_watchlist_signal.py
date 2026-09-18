# Copyright (c) 2026, Efendy (silverefendy) and Contributors
# See license.txt

from inspect import signature

from fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal import create_signal
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
