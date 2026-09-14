frappe.ui.form.on('Broker Summary', {
refresh: function(frm) {
// Add custom button for Excel import
if (!frm.doc.__islocal) {
frm.add_custom_button('Import from Excel', function() {
if (!frm.doc.excel_file) {
frappe.msgprint('Please attach an Excel file first.');
return;
}

frappe.call({
method: 'fd_trade.fd_trade.doctype.broker_summary.broker_summary.import_from_excel',
args: {
docname: frm.docname,
file_url: frm.doc.excel_file,
ticker: frm.doc.ticker
},
callback: function(r) {
if (r.message && r.message.success) {
frappe.msgprint('Import completed successfully!');
frm.reload_doc();
}
},
freeze: true,
freeze_message: 'Importing data from Excel...'
});
}, 'Actions');
}
}
});
