// BUG FIX (19 Sep 2026): client script baru untuk Trading Account Settings
// -- sebelumnya tidak ada .js sama sekali untuk DocType ini. Menambahkan
// tombol "Lihat Chart IHSG" yang reuse fungsi chart generic yang sudah ada
// (window.fd_trade_open_price_chart), tidak perlu chart/halaman baru.
frappe.ui.form.on("Trading Account Settings", {
    refresh(frm) {
        frm.add_custom_button(__("Lihat Chart IHSG"), () => {
            if (window.fd_trade_open_price_chart) {
                window.fd_trade_open_price_chart("^JKSE");
            } else {
                frappe.msgprint(__("Modul chart belum termuat. Coba refresh halaman."));
            }
        });
    }
});
