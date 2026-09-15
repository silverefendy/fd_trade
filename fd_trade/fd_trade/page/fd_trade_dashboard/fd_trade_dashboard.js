frappe.pages['fd-trade-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'FD-Trade Dashboard',
        single_column: true
    });

    let is_hidden = localStorage.getItem('fd_trade_hide_rupiah') === '1';

    page.add_inner_button('👁 Show/Hide Rupiah', function() {
        is_hidden = !is_hidden;
        localStorage.setItem('fd_trade_hide_rupiah', is_hidden ? '1' : '0');
        render_dashboard();
    });

    function format_rp(value) {
        if (is_hidden) return 'Rp ••••••';
        if (!value) return 'Rp 0';
        return 'Rp ' + frappe.format(value, {fieldtype: 'Currency'}).replace('Rp', '').trim();
    }

    function render_dashboard() {
        frappe.call({
            method: 'fd_trade.fd_trade.page.fd_trade_dashboard.fd_trade_dashboard.get_dashboard_data',
            callback: function(r) {
                let d = r.message;

                let summary_html = `
                    <div class="row" style="margin-bottom: 20px;">
                        <div class="col-sm-3">
                            <div style="padding:15px;border:1px solid #d1d8dd;border-radius:8px;">
                                <div style="font-size:12px;color:#8d99a6;">Modal Total</div>
                                <div style="font-size:20px;font-weight:600;">${format_rp(d.modal_total)}</div>
                            </div>
                        </div>
                        <div class="col-sm-3">
                            <div style="padding:15px;border:1px solid #d1d8dd;border-radius:8px;">
                                <div style="font-size:12px;color:#8d99a6;">Total Exposure</div>
                                <div style="font-size:20px;font-weight:600;">${format_rp(d.total_exposure)}</div>
                            </div>
                        </div>
                        <div class="col-sm-3">
                            <div style="padding:15px;border:1px solid #d1d8dd;border-radius:8px;">
                                <div style="font-size:12px;color:#8d99a6;">Open Positions</div>
                                <div style="font-size:20px;font-weight:600;">${d.open_count}</div>
                            </div>
                        </div>
                        <div class="col-sm-3">
                            <div style="padding:15px;border:1px solid #d1d8dd;border-radius:8px;">
                                <div style="font-size:12px;color:#8d99a6;">Watchlist</div>
                                <div style="font-size:20px;font-weight:600;">${d.watchlist_count}</div>
                            </div>
                        </div>
                    </div>
                `;

                let positions_html = '<h4>Open Positions</h4><table class="table table-bordered"><thead><tr>' +
                    '<th>Ticker</th><th>Entry</th><th>Stop Loss</th><th>Target</th><th>Lot</th><th>Risk (Rp)</th><th>Date</th>' +
                    '</tr></thead><tbody>';
                d.open_positions.forEach(function(p) {
                    positions_html += `<tr>
                        <td><a href="/app/trade-journal/${p.name}">${p.ticker}</a></td>
                        <td>${format_rp(p.entry_price)}</td>
                        <td>${format_rp(p.stop_loss)}</td>
                        <td>${format_rp(p.target_price)}</td>
                        <td>${p.position_lot || '-'}</td>
                        <td>${format_rp(p.risk_amount)}</td>
                        <td>${p.date ? frappe.datetime.str_to_user(p.date) : '-'}</td>
                    </tr>`;
                });
                positions_html += '</tbody></table>';

                let watchlist_html = '<h4>Watchlist</h4><table class="table table-bordered"><thead><tr>' +
                    '<th>Ticker</th><th>Tier</th><th>Sektor</th><th>Support</th><th>Resistance</th>' +
                    '</tr></thead><tbody>';
                d.watchlist.forEach(function(w) {
                    watchlist_html += `<tr>
                        <td><a href="/app/watchlist/${w.name}">${w.ticker}</a></td>
                        <td>${w.tier || '-'}</td>
                        <td>${w.sector || '-'}</td>
                        <td>${format_rp(w.support_level)}</td>
                        <td>${format_rp(w.resistance_level)}</td>
                    </tr>`;
                });
                watchlist_html += '</tbody></table>';

                $(page.body).html(summary_html + positions_html + '<br>' + watchlist_html);
            }
        });
    }

    render_dashboard();
};
