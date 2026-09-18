frappe.listview_settings["IHSG Signal"] = {
    formatters: {
        market_regime: (value) => {
            if (!value) return "";
            const colors = {"Risk-On": "#2e7d32", "Neutral": "#9e9e9e", "Risk-Off": "#e57373", "Avoid New Entry": "#c62828"};
            const bg = colors[value] || "#9e9e9e";
            return `<span style="background-color: ${bg}; color: white; padding: 2px 8px; border-radius: 3px;">${value}</span>`;
        }
    }
};
