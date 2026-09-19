(function () {
    const CDN = "https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js";

    function loadCharts(done) {
        if (window.LightweightCharts) return done();
        const script = document.createElement("script");
        script.src = CDN;
        script.onload = done;
        script.onerror = () => frappe.msgprint("Library chart tidak dapat dimuat dari CDN.");
        document.head.appendChild(script);
    }

    function open_chart(ticker) {
        const dialog = new frappe.ui.Dialog({
            title: `Chart ${ticker}`,
            fields: [
                {fieldtype: "HTML", fieldname: "chart_area"},
                {fieldtype: "Select", fieldname: "timeframe", label: "Timeframe", options: "Daily\nHourly", default: "Daily"},
                {fieldtype: "Int", fieldname: "lookback_days", label: "Lookback (hari)", default: 90}
            ],
            primary_action_label: "Refresh",
            primary_action: () => render(dialog, ticker)
        });
        dialog.show();
        dialog.set_value("timeframe", "Daily");
        render(dialog, ticker);
    }

    function render(dialog, ticker) {
        const timeframe = dialog.get_value("timeframe");
        if (timeframe === "Hourly") {
            frappe.msgprint("Timeframe Hourly segera hadir.");
            dialog.set_value("timeframe", "Daily");
            return;
        }
        const days = Number(dialog.get_value("lookback_days") || 90);
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Price History",
                filters: {ticker: ticker, timeframe: "Daily"},
                fields: ["date", "open", "high", "low", "close", "volume"],
                order_by: "date desc",
                limit_page_length: days
            },
            callback: (history_response) => {
                const history = (history_response.message || []).reverse();
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Watchlist Signal",
                        filters: {ticker: ticker},
                        fields: ["detected_patterns"],
                        order_by: "timestamp desc",
                        limit_page_length: 1
                    },
                    callback: (signal_response) => draw(dialog, history, signal_response.message && signal_response.message[0])
                });
            }
        });
    }

    function draw(dialog, history, latest_signal) {
        const wrapper = dialog.fields_dict.chart_area.$wrapper;
        wrapper.html('<div class="fd-trade-price-chart" style="height:520px;width:100%;"></div>');
        if (!history.length) {
            wrapper.html('<p class="text-muted">Belum ada Price History untuk ticker ini.</p>');
            return;
        }
        const container = wrapper.find(".fd-trade-price-chart")[0];
        const chart = LightweightCharts.createChart(container, {
            width: container.clientWidth || 850,
            height: 500,
            layout: {background: {color: "#ffffff"}, textColor: "#333333"},
            rightPriceScale: {borderColor: "#dddddd"},
            timeScale: {borderColor: "#dddddd", timeVisible: false}
        });
        const candles = chart.addCandlestickSeries({upColor: "#2e7d32", downColor: "#c62828", borderVisible: false, wickUpColor: "#2e7d32", wickDownColor: "#c62828"});
        candles.setData(history.map(row => ({time: row.date, open: row.open, high: row.high, low: row.low, close: row.close})));
        const patterns = latest_signal && latest_signal.detected_patterns ? JSON.parse(latest_signal.detected_patterns) : [];
        patterns.forEach(pattern => {
            const color = pattern.direction === "Bullish" ? "#2e7d32" : "#c62828";
            const tentative = pattern.confidence_level === "tentative";
            const line = chart.addLineSeries({color: color, lineWidth: tentative ? 1 : 2, lineStyle: 2, crosshairMarkerVisible: false});
            line.setData((pattern.key_points || []).map(point => ({time: point.date, value: point.price})));
            line.setMarkers((pattern.key_points || []).map(point => ({time: point.date, position: pattern.direction === "Bullish" ? "belowBar" : "aboveBar", color: color, shape: "circle", text: `${pattern.pattern_name}${tentative ? " (tentative)" : ""}`})));
        });
        chart.timeScale().fitContent();
    }

    window.fd_trade_open_price_chart = open_chart;
}());
