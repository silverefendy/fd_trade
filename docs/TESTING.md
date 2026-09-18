# FD-Trade test suite

Jalankan dari root bench dengan mode mock (default):

```bash
bench --site trace.ciptamebel.co.id run-tests --app fd_trade
```

Mode mock tidak boleh melakukan koneksi yfinance. Semua pemanggilan Telegram
di-test melalui mock dan tidak pernah mengirim pesan ke Bot API.

Untuk smoke test yfinance terbatas, aktifkan mode live:

```bash
FD_TRADE_TEST_LIVE=1 bench --site trace.ciptamebel.co.id run-tests --app fd_trade
```

Atau gunakan wrapper:

```bash
./run_all_tests.sh
./run_all_tests.sh --live
```

Test live hanya menguji ticker likuid dan akan di-skip jika Yahoo Finance tidak
tersedia. Data database test dikelola oleh `FrappeTestCase`; test tidak memakai
`frappe.db.commit()` eksplisit untuk fixture bisnis.
