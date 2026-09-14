frappe.ui.form.on('Trade Journal', {
    refresh(frm) {
        if (!frm.is_new() && frm.doc.ticker) {
            frm.add_custom_button('Fetch Support/Resistance', () => {
                frappe.call({
                    method: 'fd_trade.fd_trade.doctype.trade_journal.trade_journal.fetch_support_resistance',
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
