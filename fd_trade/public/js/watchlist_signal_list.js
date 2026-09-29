function fmtNum(value) {
    if (!value) return "";
    return Number(value).toLocaleString("id-ID", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

frappe.listview_settings["Watchlist Signal"] = {
    onload: function (listview) {
        // BUG FIX (19 Sep 2026): banner Trend/S/R IHSG, sama seperti di
        // Watchlist -- fungsi shared di ihsg_banner.js.
        fd_trade_show_ihsg_banner(listview);

        listview.page.add_inner_button("Fetch dari Watchlist", () => {
            frappe.confirm(
                "Ambil data terbaru dari semua Watchlist dan buat Watchlist Signal baru? Setiap ticker akan mendapat 1 baris signal baru.",
                () => {
                    frappe.call({
                        method: "fd_trade.tasks.refresh_all_watchlist_now",
                        freeze: true,
                        freeze_message: "Mengambil data Watchlist dan membuat signal baru (sekitar 20-30 detik)...",
                        callback: () => {
                            listview.refresh();
                            frappe.show_alert({
                                message: "Signal berhasil dibuat dari Watchlist terbaru. Ingat: data yfinance delay 15-20 menit.",
                                indicator: "green"
                            });
                        }
                    });
                }
            );
        });

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
            // Prioritas 1 (22 Sep 2026): proximity_category, konsisten dgn
            // warna badge proximity yg sudah ada -- "mendekati support"
            // pakai warna Support (merah), "mendekati resistance" pakai
            // warna Resistance (hijau), sama palet dgn Watchlist.
            if (doc.proximity_category === "mendekati support") {
                color = "#c62828";
            } else if (doc.proximity_category === "mendekati resistance") {
                color = "#2e7d32";
            } else if (doc.recommendation_price_low && value <= doc.recommendation_price_low) {
                // Fallback (logic lama): kalau proximity_category kosong,
                // tetap pakai zona beli/jual sebagai acuan.
                color = "#2e7d32";
            } else if (doc.recommendation_price_high && value >= doc.recommendation_price_high) {
                color = "#c62828";
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
