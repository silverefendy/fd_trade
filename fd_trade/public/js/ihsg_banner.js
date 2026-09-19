// BUG FIX (19 Sep 2026): fungsi shared untuk banner Trend/S/R IHSG, dipakai
// di lebih dari satu list view (Watchlist, Watchlist Signal). Sebelumnya
// logic ini duplikat kalau ditulis ulang per file -- sekarang satu sumber,
// mudah dipanggil dari onload() list view manapun yang butuh.
window.fd_trade_show_ihsg_banner = function (listview) {
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Trading Account Settings",
            fieldname: [
                "ihsg_current_price", "ihsg_trend",
                "ihsg_support", "ihsg_support_2",
                "ihsg_resistance", "ihsg_resistance_2",
                "ihsg_last_updated",
            ],
        },
        callback: (r) => {
            if (!r.message) return;
            const d = r.message;
            if (!d.ihsg_current_price) return;

            const trend_colors = {
                "Bullish Kuat": "#2e7d32",
                "Bullish Lemah": "#81c784",
                "Sideways": "#9e9e9e",
                "Bearish Lemah": "#e57373",
                "Bearish Kuat": "#c62828",
            };
            const trend_bg = trend_colors[d.ihsg_trend] || "#e0e0e0";
            const fmt = (v) => v ? format_number(v, null, 2) : "-";

            const html = `
                <span style="background-color: ${trend_bg}; color: white; padding: 2px 8px; border-radius: 3px; font-weight: 600;">
                    IHSG: ${d.ihsg_trend || "-"}
                </span>
                <span style="margin-left: 10px;">
                    Current: <b>${fmt(d.ihsg_current_price)}</b>
                </span>
                <span style="margin-left: 10px; color: #c62828;">
                    Support: ${fmt(d.ihsg_support)} / ${fmt(d.ihsg_support_2)}
                </span>
                <span style="margin-left: 10px; color: #2e7d32;">
                    Resistance: ${fmt(d.ihsg_resistance)} / ${fmt(d.ihsg_resistance_2)}
                </span>
                <span style="margin-left: 10px; color: #9e9e9e; font-size: 11px;">
                    (update: ${d.ihsg_last_updated ? frappe.datetime.str_to_user(d.ihsg_last_updated) : "-"})
                </span>
            `;
            listview.page.add_inner_message(html);
        },
    });
};
