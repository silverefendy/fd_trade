#!/usr/bin/env bash
set -o pipefail

SITE="${FRAPPE_SITE:-trace.ciptamebel.co.id}"
LIVE=0
if [[ "${1:-}" == "--live" ]]; then LIVE=1; fi

echo "FD-Trade test suite | site=${SITE} | mode=$([[ $LIVE -eq 1 ]] && echo live || echo mock)"
if [[ "$LIVE" -eq 1 ]]; then
  export FD_TRADE_TEST_LIVE=1
else
  export FD_TRADE_TEST_LIVE=0
fi

bench --site "$SITE" run-tests --app fd_trade
status=$?

echo
echo "| Suite | Result |"
echo "|---|---|"
if [[ "$status" -eq 0 ]]; then
  echo "| fd_trade (Doctype + utility + tasks) | PASS |"
  if [[ "$LIVE" -eq 0 ]]; then
    echo "Mock tests PASS. Jalankan ulang dengan --live untuk smoke test yfinance opsional."
  fi
else
  echo "| fd_trade (Doctype + utility + tasks) | FAIL |"
fi
exit "$status"
