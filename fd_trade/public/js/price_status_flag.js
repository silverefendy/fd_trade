// Tanda "Tanpa Data Harga" di form (29 Sep 2026).
// Sumber data: field Watchlist.price_status, diisi otomatis oleh
// create_signal() (watchlist_signal.py). Handler frappe.ui.form.on dari
// file ini DITAMBAHKAN ke handler form yang sudah ada, tidak menimpanya.
(function () {
    function show_flag(frm, ticker) {
        frm.dashboard.set_headline_alert(
            __("Ticker {0} tercatat TANPA DATA HARGA (mis. disuspend BEI atau data yfinance tidak tersedia). Harga yang tampil adalah harga terakhir yang diketahui, bukan harga live.", [ticker]),
            "red"
        );
    }

    function check_watchlist(frm, ticker) {
        if (!ticker) return;
        frappe.db.get_value("Watchlist", ticker, "price_status").then((r) => {
            if (r && r.message && r.message.price_status === "Tanpa Data Harga") {
                show_flag(frm, ticker);
            }
        });
    }

    frappe.ui.form.on("Watchlist", {
        refresh(frm) {
            if (frm.doc.price_status === "Tanpa Data Harga") {
                show_flag(frm, frm.doc.ticker || frm.doc.name);
            }
        },
    });

    frappe.ui.form.on("Trade Journal", {
        refresh(frm) {
            if (frm.doc.status !== "Closed") {
                check_watchlist(frm, frm.doc.ticker);
            }
        },
        ticker(frm) {
            if (frm.doc.status !== "Closed") {
                check_watchlist(frm, frm.doc.ticker);
            }
        },
    });

    frappe.ui.form.on("Price Alert", {
        refresh(frm) {
            check_watchlist(frm, frm.doc.ticker);
        },
    });
})();
