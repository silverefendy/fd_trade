"""Refresh SEMUA data lalu verifikasi. Jalankan: %run /tmp/refresh_all_20sep.py
- Telegram diredam selama proses (S/R baru bisa membalik banyak rekomendasi sekaligus).
- Urutan: harga history -> Watchlist (S/R, volume, signal) -> Trade Journal Open (S/R).
"""
import sys
import time
import frappe

# pastikan modul terkait sudah ter-import supaya ikut diredam
import fd_trade.utils.telegram  # noqa: F401
import fd_trade.tasks as tasks
import fd_trade.fd_trade.doctype.watchlist_signal.watchlist_signal  # noqa: F401
import fd_trade.fd_trade.doctype.watchlist.watchlist as wl_mod

START = frappe.utils.now_datetime()
muted, _patched = [], []


def _mute(msg=None, *a, **k):
    muted.append(str(msg or ""))
    return True


for _name, _mod in list(sys.modules.items()):
    if _name.startswith("fd_trade") and _mod is not None and hasattr(_mod, "send_telegram_notification"):
        _patched.append((_mod, _mod.send_telegram_notification))
        _mod.send_telegram_notification = _mute


def run(name):
    fn = getattr(tasks, name, None)
    if fn is None:
        print(f"SKIP  {name} (tidak ada di tasks.py)")
        return
    t0 = time.time()
    try:
        res = fn()
        frappe.db.commit()
        print(f"OK    {name} ({time.time() - t0:.0f} dtk) -> {res}")
    except Exception:
        frappe.db.rollback()
        print(f"FAIL  {name}")
        print(frappe.get_traceback())


try:
    print("=" * 66)
    run("refresh_price_history_daily")
    run("refresh_all_watchlist")

    # jaring pengaman: refresh manual untuk baris Watchlist yang belum ter-update
    stale = [r.name for r in frappe.get_all("Watchlist", fields=["name", "last_updated"])
             if not r.last_updated or r.last_updated < START]
    if stale:
        print(f"\nBelum ter-update oleh job ({len(stale)}): {stale} -> refresh manual satu per satu")
        for nm in stale:
            try:
                wl_mod.fetch_support_resistance(nm)
                print(f"  OK   {nm}")
            except Exception as e:
                print(f"  FAIL {nm}: {e}")
            time.sleep(1)

    run("refresh_open_trades_sr")
finally:
    for _mod, _orig in _patched:
        _mod.send_telegram_notification = _orig

# ---------------- VERIFIKASI ----------------
meta = frappe.get_meta("Watchlist")
want = ["ticker", "current_price", "support_level", "support_level_2", "support_level_3",
        "resistance_level", "resistance_level_2", "resistance_level_3", "trend_status",
        "volume_status", "avg_volume_20d", "last_updated"]
fields = [x for x in want if meta.has_field(x)]
rows = frappe.get_all("Watchlist", fields=["name"] + fields, order_by="name")

problems, ok = {}, 0


def flag(tk, msg):
    problems.setdefault(tk, []).append(msg)


for r in rows:
    tk, p = r.name, float(r.current_price or 0)
    S = [float(r.get(k) or 0) for k in ("support_level", "support_level_2", "support_level_3")]
    R = [float(r.get(k) or 0) for k in ("resistance_level", "resistance_level_2", "resistance_level_3")]
    if not p:
        flag(tk, "harga kosong")
    if 0 in S or 0 in R:
        flag(tk, f"level kosong S={S} R={R}")
    if not (S[0] > S[1] > S[2] > 0 or 0 in S):
        flag(tk, f"urutan S tidak menurun {S}")
    if not (0 < R[0] < R[1] < R[2] or 0 in R):
        flag(tk, f"urutan R tidak menaik {R}")
    if p and S[0] >= p:
        flag(tk, f"S1 {S[0]:g} >= harga {p:g}")
    if p and R[0] and R[0] <= p:
        flag(tk, f"R1 {R[0]:g} <= harga {p:g}")
    if p and S[0] and 0 < (p - S[0]) / p < 0.01:
        flag(tk, f"S1 hanya {(p - S[0]) / p * 100:.1f}% di bawah harga")
    if p and R[0] and 0 < (R[0] - p) / p < 0.01:
        flag(tk, f"R1 hanya {(R[0] - p) / p * 100:.1f}% di atas harga (noise)")
    if not r.get("volume_status"):
        flag(tk, "volume_status kosong")
    if not r.last_updated or r.last_updated < START:
        flag(tk, "last_updated belum baru")
    if tk not in problems:
        ok += 1

n_sig = frappe.db.count("Watchlist Signal", {"creation": (">=", START)})
print("\n" + "=" * 66)
print(f"WATCHLIST: {len(rows)} baris | bersih: {ok} | bermasalah: {len(problems)}")
print(f"Watchlist Signal baru sejak refresh: {n_sig}")
for tk, msgs in problems.items():
    print(f"  {tk}: " + " | ".join(msgs))
print(f"\nTelegram yang DIREDAM ({len(muted)} pesan) -- tidak terkirim:")
for m in muted:
    print("  -", (m.strip().splitlines() or [""])[0][:100])
print("=" * 66)
