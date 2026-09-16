frappe.ui.form.on('Watchlist', {
    refresh(frm) {
        if (!frm.is_new() && frm.doc.ticker) {
            frm.add_custom_button('Refresh Harga Sekarang', () => {
                frappe.call({
                    method: 'fd_trade.fd_trade.doctype.watchlist.watchlist.refresh_current_price',
                    args: { docname: frm.doc.name },
                    freeze: true,
                    freeze_message: 'Mengambil harga terbaru...',
                    callback: (r) => {
                        if (r.message) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message: 'Harga berhasil di-refresh. Ingat: data yfinance delay 15-20 menit, konfirmasi manual sebelum eksekusi.',
                                indicator: 'green'
                            });
                        }
                    }
                });
            });

            frm.add_custom_button('Fetch Support/Resistance', () => {
                frappe.call({
                    method: 'fd_trade.fd_trade.doctype.watchlist.watchlist.fetch_support_resistance',
                    args: { docname: frm.doc.name },
                    freeze: true,
                    freeze_message: 'Mengambil data harga dari yfinance...',
                    callback: (r) => {
                        if (r.message) {
                            frm.reload_doc();
                            frappe.show_alert({ message: 'Support/Resistance berhasil diupdate', indicator: 'green' });
                        }
                    }
                });
            });
        }
    }
});
