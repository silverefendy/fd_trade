"""
Signal Source Controller
Screening layer for informal tips from Telegram/Discord groups.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class SignalSource(Document):
    """Signal Source entry for tracking informal trading tips."""

    def on_update(self):
        """Auto-promote ke Watchlist kalau status diubah manual jadi
        'Promoted to Watchlist' lewat form (bukan lewat tombol/API langsung).
        Guard: skip kalau Watchlist untuk Signal Source ini sudah ada,
        supaya tidak dobel-promote tiap kali dokumen di-save ulang."""
        if self.status == "Promoted to Watchlist":
            already_promoted = frappe.db.exists("Watchlist", {"signal_source": self.name})
            if not already_promoted:
                promote_to_watchlist(self.name)

    pass


@frappe.whitelist()
def calculate_reliability_score(source_name):
    """Hitung reliability_score berbasis histori realisasi trade dari source_name
    yang sama. Pendekatan saat ini: cocokkan via ticker + status Closed pada
    Trade Journal (BUKAN link eksplisit -- skema saat ini tidak punya field
    penghubung langsung Signal Source -> Trade Journal).

    KETERBATASAN JUJUR: kalau ticker yang sama pernah di-trade dari sumber
    LAIN juga (bukan dari signal ini), trade itu akan ikut terhitung --
    skor ini estimasi, bukan pelacakan presisi 100%. Untuk akurasi penuh,
    perlu tambah field link eksplisit Signal Source -> Trade Journal
    sebagai perubahan skema terpisah di kemudian hari.

    Skor juga TIDAK bermakna statistik dengan sample kecil -- perhatikan
    sample_size sebelum mempercayai angka score.
    """
    import frappe

    signals = frappe.get_all(
        "Signal Source",
        filters={"source_name": source_name, "status": "Promoted to Watchlist"},
        fields=["name", "ticker"]
    )

    total, wins = 0, 0
    for sig in signals:
        trades = frappe.get_all(
            "Trade Journal",
            filters={"ticker": sig.ticker, "status": "Closed"},
            fields=["result_r"]
        )
        for t in trades:
            if t.result_r is not None:
                total += 1
                if t.result_r > 0:
                    wins += 1

    if total == 0:
        return {"score": None, "sample_size": 0, "note": "Belum ada trade selesai untuk dihitung."}

    score = round((wins / total) * 100, 1)
    confidence_note = (
        "PERINGATAN: sample masih kecil (<10), jangan jadikan acuan utama."
        if total < 10 else "Sample cukup untuk indikasi awal."
    )
    return {
        "score": score,
        "sample_size": total,
        "note": f"{wins}/{total} trade profitable. {confidence_note}"
    }

@frappe.whitelist()
def promote_to_watchlist(signal_source_name):
    """Buat Watchlist baru dari Signal Source, link balik ke asalnya,
    lalu ubah status Signal Source jadi 'Promoted to Watchlist'.
    Return nama Watchlist baru (dipakai client script untuk redirect)."""
    sig = frappe.get_doc("Signal Source", signal_source_name)

    if not sig.ticker:
        frappe.throw(_("Signal Source {0} tidak punya ticker, tidak bisa di-promote.").format(sig.name))

    already_promoted = frappe.db.exists("Watchlist", {"signal_source": sig.name})
    if already_promoted:
        frappe.throw(
            _("Signal Source {0} sudah pernah di-promote ke Watchlist {1}.").format(sig.name, already_promoted)
        )

    duplicate_ticker = frappe.db.exists("Watchlist", {"ticker": sig.ticker})
    if duplicate_ticker:
        frappe.throw(
            _(
                "Ticker {0} sudah ada di Watchlist ({1}) dari sumber lain. "
                "Tidak bisa promote duplikat -- edit Watchlist yang ada secara manual kalau perlu."
            ).format(sig.ticker, duplicate_ticker)
        )

    new_watchlist = frappe.get_doc({
        "doctype": "Watchlist",
        "ticker": sig.ticker,
        "signal_source": sig.name,
    })
    new_watchlist.insert(ignore_permissions=True)

    if sig.status != "Promoted to Watchlist":
        sig.db_set("status", "Promoted to Watchlist", notify=False)

    return new_watchlist.name
