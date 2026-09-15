frappe.listview_settings["Watchlist"] = {
    formatters: {
        // === Harga OHLC & S/R: warna teks saja, tanpa background,
        //     supaya tidak terasa penuh warna di seluruh tabel ===

        high_price: (value) => {
            if (!value) return "";
            return `<span style="color: #388e3c;">${format_currency(value)}</span>`;
        },
        low_price: (value) => {
            if (!value) return "";
            return `<span style="color: #d32f2f;">${format_currency(value)}</span>`;
        },
        support_level: (value) => {
            if (!value) return "";
            return `<span style="color: #388e3c;">${format_currency(value)}</span>`;
        },
        support_level_2: (value) => {
            if (!value) return "";
            return `<span style="color: #388e3c;">${format_currency(value)}</span>`;
        },
        resistance_level: (value) => {
            if (!value) return "";
            return `<span style="color: #d32f2f;">${format_currency(value)}</span>`;
        },
        resistance_level_2: (value) => {
            if (!value) return "";
            return `<span style="color: #d32f2f;">${format_currency(value)}</span>`;
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
            return `<span style="background-color: ${bg}; color: #333; padding: 2px 8px; border-radius: 3px; font-size: 11px; white-space: nowrap;">${value}</span>`;
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
            return `<span style="background-color: ${bg}; color: #333; padding: 2px 8px; border-radius: 3px; font-size: 11px; white-space: nowrap;">${value}</span>`;
        },
    }
};
