function fmtNum(value) {
    if (!value) return "";
    return Number(value).toLocaleString("id-ID", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

frappe.listview_settings["Trade Journal"] = {
    onload: function (listview) {
        listview.page.add_inner_button(__("Close Position"), function () {
            const checked = listview.get_checked_items();
            if (checked.length === 0) {
                frappe.msgprint({
                    message: __("Pilih 1 trade (centang baris) yang mau ditutup dulu."),
                    indicator: "orange"
                });
                return;
            }
            if (checked.length > 1) {
                frappe.msgprint({
                    message: __("Pilih HANYA 1 trade sekaligus untuk ditutup. Saat ini {0} baris terpilih.", [checked.length]),
                    indicator: "orange"
                });
                return;
            }
            const doc = checked[0];
            if (doc.status === "Closed") {
                frappe.msgprint({
                    message: __("Trade {0} sudah berstatus Closed.", [doc.name]),
                    indicator: "orange"
                });
                return;
            }
            const dialog = new frappe.ui.Dialog({
                title: __("Tutup Posisi: {0} ({1})", [doc.name, doc.ticker]),
                fields: [
                    { fieldname: "exit_price", fieldtype: "Currency", label: __("Exit Price"), reqd: 1 }
                ],
                primary_action_label: __("Close"),
                primary_action: function (values) {
                    frappe.call({
                        method: "fd_trade.fd_trade.doctype.trade_journal.trade_journal.close_position",
                        args: { docname: doc.name, exit_price: values.exit_price },
                        freeze: true,
                        freeze_message: __("Menutup posisi..."),
                        callback: function (r) {
                            if (r.message) {
                                dialog.hide();
                                frappe.show_alert({
                                    message: __("Trade {0} ditutup. Result: {1}", [doc.name, frappe.format(r.message.result_rp, { fieldtype: "Currency" })]),
                                    indicator: r.message.result_rp >= 0 ? "green" : "red"
                                });
                                listview.refresh();
                            }
                        }
                    });
                }
            });
            dialog.show();
        });
    },
    formatters: {
        support_level: (value) => {
            if (!value) return "";
            return `<span style="color: #c62828;">${fmtNum(value)}</span>`;
        },
        support_level_2: (value) => {
            if (!value) return "";
            return `<span style="color: #ef9a9a;">${fmtNum(value)}</span>`;
        },
        resistance_level: (value) => {
            if (!value) return "";
            return `<span style="color: #2e7d32;">${fmtNum(value)}</span>`;
        },
        resistance_level_2: (value) => {
            if (!value) return "";
            return `<span style="color: #81c784;">${fmtNum(value)}</span>`;
        },
        entry_price: (value, df, doc) => {
            if (!value) return "";
            let color = "";
            if (doc.current_price) {
                color = doc.current_price > value ? "#2e7d32" : (doc.current_price < value ? "#c62828" : "");
            }
            const style = color ? `color: ${color}; font-weight: 700;` : "";
            return `<span style="${style}">${fmtNum(value)}</span>`;
        },
        stop_loss: (value, df, doc) => {
            if (!value) return "";
            let style = "";
            if (doc.current_price) {
                const dist_pct = (doc.current_price - value) / doc.current_price * 100;
                if (dist_pct <= 0) {
                    style = "color: #b71c1c; font-weight: 700;";
                    return `<span style="${style}">\u26a0 ${fmtNum(value)}</span>`;
                } else if (dist_pct <= 5) {
                    style = "color: #c62828; font-weight: 700;";
                } else if (dist_pct <= 15) {
                    style = "color: #ef6c00; font-weight: 700;";
                }
            }
            return `<span style="${style}">${fmtNum(value)}</span>`;
        },
        current_price: (value, df, doc) => {
            if (!value) return "";
            const threshold_pct = 1;
            const levels = [
                { field: "support_level", color: "#c62828" },
                { field: "support_level_2", color: "#ef9a9a" },
                { field: "resistance_level", color: "#2e7d32" },
                { field: "resistance_level_2", color: "#81c784" },
            ];
            let closest_color = null;
            let closest_diff = Infinity;
            levels.forEach((l) => {
                const lvl_value = doc[l.field];
                if (lvl_value) {
                    const diff_pct = Math.abs(value - lvl_value) / lvl_value * 100;
                    if (diff_pct <= threshold_pct && diff_pct < closest_diff) {
                        closest_diff = diff_pct;
                        closest_color = l.color;
                    }
                }
            });
            const style = closest_color ? `color: ${closest_color}; font-weight: 700;` : "";
            return `<span style="${style}">${fmtNum(value)}</span>`;
        },
        status: (value) => {
            if (!value) return "";
            const colors = { "Open": "#ef6c00", "Closed": "#616161" };
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px;">${value}</span>`;
        },
        trend: (value) => {
            if (!value) return "";
            const colors = {
                "Bullish Kuat": "#1b5e20",
                "Bullish Lemah": "#66bb6a",
                "Sideways": "#9e9e9e",
                "Bearish Lemah": "#ef9a9a",
                "Bearish Kuat": "#b71c1c",
            };
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px;">${value}</span>`;
        },
        trading_mode: (value) => {
            if (!value) return "";
            const colors = { "Normal": "#9e9e9e", "Fast": "#1565c0" };
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px;">${value}</span>`;
        },
        position_lot: (value, df, doc) => {
            if (!value) return "0";
            let color = "#2e7d32";
            if (doc.risk_amount && doc.entry_price && doc.stop_loss) {
                const risk_per_share = doc.entry_price - doc.stop_loss;
                if (risk_per_share > 0) {
                    const actual_risk = value * 100 * risk_per_share;
                    if (actual_risk > doc.risk_amount * 1.2) {
                        color = "#c62828";
                    }
                }
            }
            return `<span style="color: ${color}; font-weight: 700;">${fmtNum(value)}</span>`;
        },
        suggested_lot: (value) => fmtNum(value),
        risk_amount: (value) => fmtNum(value),
    }
};
