frappe.listview_settings["Watchlist"] = {
    formatters: {
        // === Harga OHLC & S/R: warna teks saja, tanpa background,
        //     supaya tidak terasa penuh warna di seluruh tabel ===

        high_price: (value) => {
            if (!value) return "";
            return `<span style="color: #388e3c;">${format_number(value, null, 0)}</span>`;
        },
        low_price: (value) => {
            if (!value) return "";
            return `<span style="color: #d32f2f;">${format_number(value, null, 0)}</span>`;
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
            const style = closest_color
                ? `color: ${closest_color}; font-weight: 700;`
                : "";
            return `<span style="${style}">${format_number(value, null, 0)}</span>`;
        },
        support_level: (value) => {
            if (!value) return "";
            return `<span style="color: #c62828;">${format_number(value, null, 0)}</span>`;
        },
        support_level_2: (value) => {
            if (!value) return "";
            return `<span style="color: #ef9a9a;">${format_number(value, null, 0)}</span>`;
        },
        resistance_level: (value) => {
            if (!value) return "";
            return `<span style="color: #2e7d32;">${format_number(value, null, 0)}</span>`;
        },
        resistance_level_2: (value) => {
            if (!value) return "";
            return `<span style="color: #81c784;">${format_number(value, null, 0)}</span>`;
        },

        // === Kategori: badge dengan warna pastel/muted (bukan warna terang),
        //     teks gelap supaya kontras tetap nyaman dibaca ===

        sector: (value) => {
            if (!value) return "";
            const sector_colors = {
                "Energi": "#d7ccc8",
                "Barang Baku": "#bcaaa4",
                "Perindustrian": "#cfd8dc",
                "Konsumen Primer": "#c8e6c9",
                "Konsumen Non-Primer": "#dcedc8",
                "Kesehatan": "#b2ebf2",
                "Keuangan": "#bbdefb",
                "Properti & Real Estat": "#e1bee7",
                "Teknologi": "#c5cae9",
                "Infrastruktur": "#ffe0b2",
                "Transportasi & Logistik": "#ffccbc",
            };
            const bg = sector_colors[value] || "#e0e0e0";
            return `<span style="background-color: ${bg}; color: #333; padding: 2px 8px; border-radius: 3px; white-space: nowrap;">${value}</span>`;
        },

        trend_status: (value) => {
            if (!value) return "";
            const colors = {
                "Bullish Kuat": "#2e7d32",
                "Bullish Lemah": "#81c784",
                "Sideways": "#9e9e9e",
                "Bearish Lemah": "#e57373",
                "Bearish Kuat": "#c62828",
            };
            const bg = colors[value] || "#e0e0e0";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px; white-space: nowrap;">${value}</span>`;
        },

        tier: (value) => {
            if (!value) return "";
            const tier_colors = { "A": "#c8e6c9", "B": "#fff9c4", "C": "#e0e0e0" };
            const bg = tier_colors[value] || "#e0e0e0";
            return `<span style="background-color: ${bg}; color: #333; padding: 2px 8px; border-radius: 3px; font-weight: 600;">${value}</span>`;
        },

        // Stock Group: isi dinamis (Link field), warna auto dari hash nama,
        // dibatasi ke palet pastel yang sama supaya tetap konsisten gaya
        stock_group: (value) => {
            if (!value) return "";
            const palette = [
                "#bbdefb", "#c8e6c9", "#ffe0b2", "#e1bee7",
                "#b2dfdb", "#ffcdd2", "#c5cae9", "#d7ccc8",
            ];
            let hash = 0;
            for (let i = 0; i < value.length; i++) {
                hash = value.charCodeAt(i) + ((hash << 5) - hash);
            }
            const bg = palette[Math.abs(hash) % palette.length];
            return `<span style="background-color: ${bg}; color: #333; padding: 2px 8px; border-radius: 3px; white-space: nowrap;">${value}</span>`;
        },
    },

    onload(listview) {
        listview.page.add_inner_button("Lihat Chart", () => {
            const selected = listview.get_checked_items();
            if (!selected.length) return frappe.msgprint("Pilih satu ticker Watchlist terlebih dahulu.");
            window.fd_trade_open_price_chart(selected[0].name);
        });

        listview.page.add_inner_button("Refresh Semua Harga", () => {
            frappe.call({
                method: "fd_trade.tasks.refresh_all_watchlist_now",
                freeze: true,
                freeze_message: "Mengambil harga terbaru untuk semua ticker...",
                callback: (r) => {
                    listview.refresh();
                    frappe.show_alert({
                        message: "Semua harga berhasil di-refresh. Ingat: data yfinance delay 15-20 menit.",
                        indicator: "green"
                    });
                }
            });
        });

        const style_id = "fd-trade-watchlist-column-width";
        if (document.getElementById(style_id)) return;

        const style = document.createElement("style");
        style.id = style_id;
        style.innerHTML = `
            .list-row-col[data-fieldname="ticker"] {
                max-width: 90px;
                min-width: 90px;
            }
            .list-row-col[data-fieldname="tier"] {
                max-width: 70px;
                min-width: 70px;
            }
            .list-row-col[data-fieldname="current_price"],
            .list-row-col[data-fieldname="high_price"],
            .list-row-col[data-fieldname="low_price"] {
                max-width: 130px;
                min-width: 130px;
                text-align: right;
            }
            .list-row-col[data-fieldname="last_updated"] {
                max-width: 160px;
                min-width: 160px;
            }
        `;
        document.head.appendChild(style);
    }
};
