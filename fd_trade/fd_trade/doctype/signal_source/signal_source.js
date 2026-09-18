// Copyright (c) 2026, Efendy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Signal Source", {
refresh(frm) {
const promotable_statuses = ["New", "Screening"];
const status_is_promotable = promotable_statuses.includes(frm.doc.status);

if (!frm.is_new() && status_is_promotable) {
frm.add_custom_button(__("Promote to Watchlist"), function () {
frappe.confirm(
__("Buat Watchlist baru untuk ticker {0}?", [frm.doc.ticker]),
function () {
frappe.call({
method:
"fd_trade.fd_trade.doctype.signal_source.signal_source.promote_to_watchlist",
args: {
signal_source_name: frm.doc.name,
},
freeze: true,
freeze_message: __("Membuat Watchlist..."),
callback: function (r) {
if (r.message) {
frappe.show_alert({
message: __("Watchlist berhasil dibuat: {0}", [r.message]),
indicator: "green",
});
frappe.model.clear_doc("Watchlist", r.message);
						frappe.set_route("Form", "Watchlist", r.message);
}
},
});
}
);
}).addClass("btn-primary");
}
},
});
