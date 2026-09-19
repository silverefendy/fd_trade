function fmtNum(value) {
    if (!value) return "";
    return Number(value).toLocaleString("id-ID", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

frappe.listview_settings["Watchlist Signal"] = {
    onload: function (listview) {
        listview.page.add_inner_button("Lihat Chart", () => {
            const selected = listview.get_checked_items();
            if (!selected.length) return frappe.msgprint("Pilih satu signal terlebih dahulu.");
            window.fd_trade_open_price_chart(selected[0].ticker);
        });
    },
    formatters: {
        recommendation: (value) => {
            if (!value) return "";
            const colors = {
                "Buy": "#2e7d32",
                "Sell": "#c62828",
                "Avoid": "#212121",
                "Wait": "#9e9e9e"
            };
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px; white-space: nowrap;">${value}</span>`;
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

        proximity_category: (value) => {
            if (!value) return "";
            const colors = {"mendekati support": "#c62828", "mendekati resistance": "#2e7d32", "di tengah range": "#9e9e9e"};
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px;">${value}</span>`;
        },

        volume_status: (value) => {
            if (!value) return "";
            const colors = {"Volume Tinggi": "#2e7d32", "Volume Normal": "#9e9e9e", "Volume Rendah": "#c62828"};
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px;">${value}</span>`;
        },

        current_price: (value, df, doc) => {
            if (!value) return "";
            let color = "";
            if (doc.recommendation_price_low && value <= doc.recommendation_price_low) {
                color = "#2e7d32"; // harga di/bawah zona beli -> hijau
            } else if (doc.recommendation_price_high && value >= doc.recommendation_price_high) {
                color = "#c62828"; // harga di/atas zona jual -> merah
            }
            const style = color ? `color: ${color}; font-weight: 700;` : "";
            return `<span style="${style}">${fmtNum(value)}</span>`;
        },

        recommendation_price_low: (value, df, doc) => {
            // Kolom "Recommendation Price (Low)" -- bagian bawah range, warna sesuai jenis rekomendasi
            if (!value) return "";
            if (doc.recommendation === "Buy") {
                let html = `<span style="color: #2e7d32; font-weight: 600;">${fmtNum(value)}</span>`;
                if (doc.stop_loss) {
                    html += `<br><span style="color: #c62828; font-size: 11px;">SL: ${fmtNum(doc.stop_loss)}</span>`;
                }
                return html;
            }
            if (doc.recommendation === "Sell") {
                return `<span style="color: #c62828; font-weight: 600;">${fmtNum(value)}</span>`;
            }
            return "";
        },

        recommendation_price_high: (value, df, doc) => {
            // Kolom "Recommendation Price (High)" -- bagian atas range, warna sesuai jenis rekomendasi
            if (!value) return "";
            if (doc.recommendation === "Buy") {
                return `<span style="color: #2e7d32; font-weight: 600;">${fmtNum(value)}</span>`;
            }
            if (doc.recommendation === "Sell") {
                return `<span style="color: #c62828; font-weight: 600;">${fmtNum(value)}</span>`;
            }
            return "";
        },

        suggested_position_rp: (value) => fmtNum(value),

        risk_amount: (value) => fmtNum(value),

        stop_loss: (value, df, doc) => {
            // Kosong untuk Sell (memang tidak berlaku), tampil polos tanpa "IDR" untuk Buy
            if (!value || doc.recommendation !== "Buy") return "";
            return fmtNum(value);
        }
    }
};
