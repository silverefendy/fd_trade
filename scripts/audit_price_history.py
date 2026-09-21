"""Audit Price History (read-only). Jalankan: %run /tmp/audit_price_history.py"""
import frappe

rows = frappe.db.sql(
    "SELECT ticker, `date` AS d, `open` AS o, `high` AS h, `low` AS l, `close` AS c, volume AS v "
    "FROM `tabPrice History` WHERE timeframe = 'Daily' ORDER BY ticker, `date`",
    as_dict=True,
)
by = {}
for r in rows:
    by.setdefault(r.ticker, []).append(r)

global_last = max(r.d for r in rows)
dups = frappe.db.sql(
    "SELECT ticker, `date`, COUNT(*) AS c FROM `tabPrice History` WHERE timeframe = 'Daily' "
    "GROUP BY ticker, `date` HAVING c > 1", as_dict=True)

print(f"Total baris Daily: {len(rows)} | tanggal terbaru global: {global_last} | duplikat (ticker,tanggal): {len(dups)}")
print(f"{'TICKER':8s}{'BARIS':>6s} {'AWAL':>11s} {'AKHIR':>11s} {'V=0':>5s} {'V=0&datar':>10s} {'V=0 di 20 terakhir':>19s}  CATATAN")
tot_flat = 0
for tk, rs in by.items():
    is_idx = tk.startswith("^")
    zero = [x for x in rs if not x.v]
    flat = [x for x in zero if x.o == x.h == x.l == x.c]
    last20 = sum(1 for x in rs[-20:] if not x.v)
    note = []
    if rs[-1].d < global_last:
        note.append("STALE")
    if is_idx:
        note.append("indeks: volume 0 wajar")
    elif flat:
        tot_flat += len(flat)
        note.append("baris libur/artefak")
    if last20 and not is_idx:
        note.append("MERUSAK rata2 volume 20d")
    print(f"{tk:8s}{len(rs):6d} {str(rs[0].d):>11s} {str(rs[-1].d):>11s} {len(zero):5d} {len(flat):10d} {last20:19d}  {', '.join(note)}")
print(f"\nTotal baris saham V=0 & OHLC datar (kandidat artefak hari libur): {tot_flat}")
if dups:
    print("DUPLIKAT:", dups[:10])
