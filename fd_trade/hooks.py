"""
FD-Trade App Hooks
Defines integration points with Frappe framework.
"""

app_name = "fd_trade"
app_title = "FD-Trade"
app_publisher = "Efendy (silverefendy)"
app_description = "Personal stock trading journal, risk management, and broker-flow screening system for Indonesian stock market (IDX) swing and fast trading."
app_icon = "octicon octicon-graph"
app_logo_url = "/assets/fd_trade/images/fd_trade-logo.svg"
app_color = "grey"
app_email = "silverefendy@users.noreply.github.com"
app_license = "MIT"

add_to_apps_screen = [
    {
        "name": "fd_trade",
        "logo": "/assets/fd_trade/images/fd_trade-logo.svg",
        "title": "FD-Trade",
        "route": "/desk/fd-trade",
    }
]

# Fixtures
fixtures = [
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "FD-Trade"]]
    }
]

# List View JS
doctype_list_js = {
    "Watchlist": "public/js/watchlist_list.js"
}

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
        "1-59/15 9-16 * * 1-5": [
            "fd_trade.tasks.refresh_all_watchlist"
        ],
        "3-59/30 9-16 * * 1-5": [
            "fd_trade.tasks.refresh_ihsg_trend"
        ],
        "2-59/30 9-16 * * 1-5": [
            "fd_trade.tasks.refresh_open_trades_sr"
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
