frappe.query_reports["Watchlist Berwarna"] = {
    filters: [
        {
            fieldname: "sector",
            label: "Sector",
            fieldtype: "Select",
            options: "\nEnergi\nBarang Baku\nPerindustrian\nKonsumen Primer\nKonsumen Non-Primer\nKesehatan\nKeuangan\nProperti & Real Estat\nTeknologi\nInfrastruktur\nTransportasi & Logistik",
        },
        {
            fieldname: "tier",
            label: "Tier",
            fieldtype: "Select",
            options: "\nA\nB\nC",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        const green = "#388e3c";
        const red = "#d32f2f";

        if (["high_price", "support_level", "support_level_2"].includes(column.fieldname) && data[column.fieldname]) {
            value = `<span style="color: ${green};">${value}</span>`;
        }

        if (["low_price", "resistance_level", "resistance_level_2"].includes(column.fieldname) && data[column.fieldname]) {
            value = `<span style="color: ${red};">${value}</span>`;
        }

        if (column.fieldname === "sector" && data.sector) {
            const sector_colors = {
                "Energi": "#d7ccc8", "Barang Baku": "#bcaaa4", "Perindustrian": "#cfd8dc",
                "Konsumen Primer": "#c8e6c9", "Konsumen Non-Primer": "#dcedc8", "Kesehatan": "#b2ebf2",
                "Keuangan": "#bbdefb", "Properti & Real Estat": "#e1bee7", "Teknologi": "#c5cae9",
                "Infrastruktur": "#ffe0b2", "Transportasi & Logistik": "#ffccbc",
            };
            const bg = sector_colors[data.sector] || "#e0e0e0";
            value = `<span style="background-color:${bg}; color:#333; padding:2px 8px; border-radius:3px; font-size:11px; white-space:nowrap;">${data.sector}</span>`;
        }

        if (column.fieldname === "tier" && data.tier) {
            const tier_colors = { A: "#c8e6c9", B: "#fff9c4", C: "#e0e0e0" };
            const bg = tier_colors[data.tier] || "#e0e0e0";
            value = `<span style="background-color:${bg}; color:#333; padding:2px 8px; border-radius:3px; font-weight:600;">${data.tier}</span>`;
        }

        if (column.fieldname === "stock_group" && data.stock_group) {
            const palette = ["#bbdefb", "#c8e6c9", "#ffe0b2", "#e1bee7", "#b2dfdb", "#ffcdd2", "#c5cae9", "#d7ccc8"];
            let hash = 0;
            for (let i = 0; i < data.stock_group.length; i++) {
                hash = data.stock_group.charCodeAt(i) + ((hash << 5) - hash);
            }
            const bg = palette[Math.abs(hash) % palette.length];
            value = `<span style="background-color:${bg}; color:#333; padding:2px 8px; border-radius:3px; font-size:11px; white-space:nowrap;">${data.stock_group}</span>`;
        }

        return value;
    },
};
