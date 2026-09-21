"""Backtest v2: Volume Profile(+fallback) vs swing vs uniform, dengan varian stop & filter tren (read-only).
Jalankan : %run /tmp/backtest_sr2.py
Opsi     : %run /tmp/backtest_sr2.py brief=1 step=3 rr=1.5 k=1.5 fee=0.004 tickers=DEWA,BBCA
Varian   : stop = s2 (SL di S2, seperti sistem sekarang) | atr (SL = S1 - k*ATR14)
           filter = none | ma50 (hanya sinyal bila harga > MA50)
Tidak menulis apa pun ke database. Level dihitung ulang oleh get_support_resistance() asli
untuk tiap tanggal as-of (tanpa melihat data setelah tanggal itu).
"""
import sys
import re
import bisect
from collections import defaultdict
import frappe
import fd_trade.utils.price_data as pdm
import fd_trade.utils.volume_profile as vpm

ARGS = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
STEP = int(ARGS.get("step", 5))
FILL = int(ARGS.get("fill", 10))
HOLD = int(ARGS.get("hold", 15))
RR = float(ARGS.get("rr", 1.5))
START = int(ARGS.get("start", 130))
ATRK = float(ARGS.get("k", 1.5))      # pengali ATR untuk stop varian 'atr'
FEE = float(ARGS.get("fee", 0.004))   # biaya round-trip (fraksi dari harga entry)
UD = float(ARGS.get("ud", 0.023))     # baseline seragam: jarak entry di bawah harga
UR = float(ARGS.get("ur", 0.047))     # baseline seragam: jarak stop di bawah entry
BRIEF = ARGS.get("brief", "0") == "1"
ONLY = [t.strip().upper() for t in ARGS.get("tickers", "").split(",") if t.strip()]
CFGS = [("s2", "none"), ("atr", "none"), ("s2", "ma50"), ("atr", "ma50")]
TOUCH_TOL = 0.003
WIN = 5
MAX_DIST = 0.08
MIN_RISK = 0.01
SWING_W = 5
SWING_BARS = 125
METHODS = ("VP", "SWING", "UNIFORM")

CTX = {"as_of": None, "price": None}
_orig_rows = vpm.get_price_history_rows
_orig_price = getattr(pdm, "get_current_price", None)
_patched = []


def _rows_wrapper(*a, **k):
    a = list(a)
    if len(a) >= 3:
        if a[2] is None:
            a[2] = CTX["as_of"]
    elif k.get("end_date") is None:
        k["end_date"] = CTX["as_of"]
    return _orig_rows(*a, **k)


def _price_wrapper(*a, **k):
    return CTX["price"]


def _patch_all():
    for name, mod in list(sys.modules.items()):
        if not name.startswith("fd_trade") or mod is None:
            continue
        if getattr(mod, "get_price_history_rows", None) is _orig_rows:
            _patched.append((mod, "get_price_history_rows", _orig_rows))
            mod.get_price_history_rows = _rows_wrapper
        if _orig_price and getattr(mod, "get_current_price", None) is _orig_price:
            _patched.append((mod, "get_current_price", _orig_price))
            mod.get_current_price = _price_wrapper


def _unpatch_all():
    for mod, attr, orig in _patched:
        setattr(mod, attr, orig)
    _patched.clear()


def load_rows(ticker):
    try:
        rows = _orig_rows(ticker, 750)
    except TypeError:
        rows = _orig_rows(ticker, 750, None)
    return list(rows or [])


def f(x, k):
    return float(x[k])


def atr14(rows):
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = f(rows[i], "high"), f(rows[i], "low"), f(rows[i - 1], "close")
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    seg = trs[-14:]
    return sum(seg) / len(seg) if seg else 0.0


def sma_close(rows, n):
    if len(rows) < n:
        return None
    return sum(f(x, "close") for x in rows[-n:]) / n


def pick(levels, min_gap=0.01):
    out = []
    for L in levels:
        if out and abs(L - out[-1]) / out[-1] < min_gap:
            continue
        out.append(L)
        if len(out) == 3:
            break
    return out


def swing_levels(rows, price):
    seg = rows[-SWING_BARS:]
    n = len(seg)
    lows = [f(x, "low") for x in seg]
    highs = [f(x, "high") for x in seg]
    sl, sh = set(), set()
    for i in range(SWING_W, n - SWING_W):
        if lows[i] == min(lows[i - SWING_W:i + SWING_W + 1]):
            sl.add(lows[i])
        if highs[i] == max(highs[i - SWING_W:i + SWING_W + 1]):
            sh.add(highs[i])
    sup = sorted([x for x in sl if x < price], reverse=True)
    res = sorted([x for x in sh if x > price])
    return pick(sup), pick(res)


def sys_levels(res, price):
    s = [float(res.get(k) or 0) for k in ("support_level", "support_level_2", "support_level_3")]
    r = [float(res.get(k) or 0) for k in ("resistance_level", "resistance_level_2", "resistance_level_3")]
    bad_s = bool(s[0]) and s[0] >= price * 0.999
    bad_r = bool(r[0]) and r[0] <= price * 1.001
    sup = sorted([x for x in s if x and x < price], reverse=True)
    rs = sorted([x for x in r if x and x > price])
    return sup, rs, bad_s, bad_r


def eval_support(fut, L):
    for j, row in enumerate(fut[:FILL]):
        if f(row, "low") <= L * (1 + TOUCH_TOL):
            seg = fut[j:j + WIN]
            return {"hold": min(f(x, "close") for x in seg) >= L * 0.99,
                    "move": max(f(x, "high") for x in seg) >= L * 1.03}
    return None


def eval_resistance(fut, L):
    for j, row in enumerate(fut[:FILL]):
        if f(row, "high") >= L * (1 - TOUCH_TOL):
            seg = fut[j:j + WIN]
            return {"hold": max(f(x, "close") for x in seg) <= L * 1.01,
                    "move": min(f(x, "low") for x in seg) <= L * 0.97}
    return None


def sim_long(fut, entry, sl, rr):
    """Limit buy di 'entry', stop di 'sl', target rr*R. Konservatif: di hari fill hanya
    stop yang dicek; stop diprioritaskan bila stop & target di hari yang sama."""
    risk = entry - sl
    tp = entry + rr * risk
    fd = None
    for j, row in enumerate(fut[:FILL]):
        if f(row, "low") <= entry:
            fd = j
            break
    if fd is None:
        return None
    row = fut[fd]
    o, l = f(row, "open"), f(row, "low")
    px = min(o, entry)
    if o <= sl:
        return {"R": -1.0, "out": "GAP"}
    if l <= sl:
        return {"R": (sl - px) / risk, "out": "SL"}
    for row in fut[fd + 1: fd + 1 + HOLD]:
        o, h, l = f(row, "open"), f(row, "high"), f(row, "low")
        if l <= sl:
            ex = o if o < sl else sl
            return {"R": (ex - px) / risk, "out": "SL"}
        if h >= tp:
            ex = o if o > tp else tp
            return {"R": (ex - px) / risk, "out": "TP"}
    last = fut[min(fd + HOLD, len(fut) - 1)]
    return {"R": (f(last, "close") - px) / risk, "out": "TIME"}


def bucket(dist):
    return "<1%" if dist < 0.01 else ("1-3%" if dist < 0.03 else ">=3%")


class Acc:
    def __init__(self):
        self.sig = 0
        self.skip = 0
        self.trades = []
        self.sig_by_regime = defaultdict(int)

    def merge(self, o):
        self.sig += o.sig
        self.skip += o.skip
        self.trades += o.trades
        for k, v in o.sig_by_regime.items():
            self.sig_by_regime[k] += v


class Lvl:
    def __init__(self):
        self.d = {"S": {}, "R": {}}

    def add(self, side, dist, ev):
        d = self.d[side].setdefault(bucket(dist), {"n": 0, "touch": 0, "hold": 0, "move": 0})
        d["n"] += 1
        if ev:
            d["touch"] += 1
            d["hold"] += 1 if ev["hold"] else 0
            d["move"] += 1 if ev["move"] else 0

    def merge(self, o):
        for side in ("S", "R"):
            for bk, v in o.d[side].items():
                t = self.d[side].setdefault(bk, {"n": 0, "touch": 0, "hold": 0, "move": 0})
                for k in t:
                    t[k] += v[k]


def trade_signal(acc, fut, price, s1, sl, ma50v, filt, regime=None):
    if filt == "ma50" and (ma50v is None or price <= ma50v):
        acc.skip += 1
        return
    if not s1 or sl is None or sl <= 0 or sl >= s1:
        acc.skip += 1
        return
    dist = (price - s1) / price
    if dist < 0 or dist > MAX_DIST or (s1 - sl) / s1 < MIN_RISK:
        acc.skip += 1
        return
    acc.sig += 1
    acc.sig_by_regime[regime] += 1
    t = sim_long(fut, s1, sl, RR)
    if t:
        risk = s1 - sl
        t["Rn"] = t["R"] - FEE * s1 / risk
        t["dist"] = dist
        t["riskp"] = risk / s1
        t["regime"] = regime
        acc.trades.append(t)


def stop_for(mode, s1, s2, atr):
    if mode == "atr":
        return s1 - ATRK * atr
    return s2


def pct(a, b):
    return f"{a / b * 100:5.0f}%" if b else "   n/a"


def stats(trades, key="R"):
    n = len(trades)
    if not n:
        return None
    rs = [t[key] for t in trades]
    return {"n": n, "win": sum(1 for r in rs if r > 0) / n * 100, "exp": sum(rs) / n}


def summary_table(accs, cfgs, regime_filter=None, label=None):
    if label:
        print(f"\n--- {label} ---")
    print(f"\n{'METODE':9s}{'STOP':>5s}{'FILTER':>7s}{'SINYAL':>8s}{'TERISI':>8s}{'WIN%':>6s}{'EXP(R)':>8s}{'NET(R)':>8s}{'RATA2 STOP':>11s}")
    for m in METHODS:
        for stop, filt in cfgs:
            if m == "UNIFORM" and stop != "s2":
                continue
            a = accs.get((m, stop, filt))
            if not a:
                continue
            if regime_filter is None:
                trades, sig = a.trades, a.sig
            else:
                trades = [t for t in a.trades if t.get("regime") == regime_filter]
                sig = a.sig_by_regime.get(regime_filter, 0)
            g, nn = stats(trades, "R"), stats(trades, "Rn")
            if not g:
                print(f"{m:9s}{stop:>5s}{filt:>7s}{sig:8d}{0:8d}{'n/a':>6s}{'n/a':>8s}{'n/a':>8s}")
                continue
            rk = sum(t["riskp"] for t in trades) / len(trades) * 100
            print(f"{m:9s}{stop:>5s}{filt:>7s}{sig:8d}{g['n']:8d}{g['win']:6.0f}{g['exp']:+8.2f}{nn['exp']:+8.2f}{rk:10.1f}%")


def detail(name, a, lv):
    print(f"\n=== DETAIL {name} (stop=s2, filter=none) ===")
    if a.trades:
        outs = {k: sum(1 for t in a.trades if t['out'] == k) for k in ("TP", "SL", "TIME", "GAP")}
        wins = [t["R"] for t in a.trades if t["R"] > 0]
        loss = [t["R"] for t in a.trades if t["R"] <= 0]
        print(f"avg win {sum(wins) / len(wins) if wins else 0:+.2f}R | avg loss {sum(loss) / len(loss) if loss else 0:+.2f}R | hasil {outs}")
        print("  expectancy per jarak S1 dari harga:")
        for b in ("<1%", "1-3%", ">=3%"):
            sub = [t for t in a.trades if bucket(t["dist"]) == b]
            s = stats(sub)
            print(f"    {b:>5}: trade {len(sub):3d} | " + (f"win {s['win']:.0f}% | exp {s['exp']:+.2f}R" if s else "n/a"))
    for side, lab in (("S", "SUPPORT S1 (hold = tak ada close < level-1% dlm 5 hari)"),
                      ("R", "RESISTANCE R1 (hold = tak ada close > level+1% dlm 5 hari)")):
        print(f"  {lab}")
        for b in ("<1%", "1-3%", ">=3%"):
            d = lv.d[side].get(b)
            if d:
                print(f"    jarak {b:>5}: level {d['n']:4d} | tersentuh {pct(d['touch'], d['n'])} | hold|sentuh {pct(d['hold'], d['touch'])}")


def load_ihsg_regime():
    """Hitung ulang rezim IHSG per-hari dari tabPrice History (^JKSE), bukan dari tabel
    IHSG Signal (baru mulai terisi 18 Sep 2026, cuma 3 record -- tidak cukup historis)."""
    rows = frappe.db.sql(
        "select date, close from `tabPrice History` "
        "where ticker='^JKSE' and timeframe='Daily' order by date",
        as_dict=True,
    )
    dates = [r["date"] for r in rows]
    closes = [float(r["close"]) for r in rows]
    n = len(closes)
    regimes = [None] * n
    for i in range(n):
        if i < 199:
            continue
        ma50 = sum(closes[i - 49:i + 1]) / 50
        ma200 = sum(closes[i - 199:i + 1]) / 200
        px = closes[i]
        if px > ma50 > ma200:
            regimes[i] = "Bullish"
        elif px < ma50 < ma200:
            regimes[i] = "Bearish"
        else:
            regimes[i] = "Sideways"
    return dates, regimes


def regime_for_date(dates, regimes, as_of):
    idx = bisect.bisect_right(dates, as_of) - 1
    return regimes[idx] if idx >= 0 else None


def main():
    tickers = ONLY or frappe.db.sql_list(
        "select distinct ticker from `tabPrice History` where timeframe='Daily' and left(ticker, 1) <> '^' order by ticker")
    accs = {}
    lvls = {"VP": Lvl(), "SWING": Lvl()}
    per = []
    raw = {"n": 0, "s": 0, "r": 0, "fail": 0}
    checked = 0
    ihsg_dates, ihsg_regimes = load_ihsg_regime()
    n_reg = sum(1 for r in ihsg_regimes if r)
    print(f"IHSG regime terhitung: {n_reg} hari (dari {len(ihsg_dates)} baris ^JKSE)")
    _patch_all()
    try:
        for tk in tickers:
            rows = load_rows(tk)
            n = len(rows)
            if n < START + FILL + HOLD + 5:
                print(f"skip {tk}: data {n} baris kurang")
                continue
            loc = {}
            for i in range(START, n - 1 - (FILL + HOLD) + 1, STEP):
                as_of, price = rows[i]["date"], f(rows[i], "close")
                fut = rows[i + 1: i + 1 + FILL + HOLD]
                CTX["as_of"], CTX["price"] = as_of, price
                regime = regime_for_date(ihsg_dates, ihsg_regimes, as_of)
                try:
                    res = pdm.get_support_resistance(tk)
                except Exception:
                    res = None
                if not res:
                    raw["fail"] += 1
                    continue
                used = res.get("price_history_rows") or []
                if used and used[-1]["date"] != as_of:
                    raise RuntimeError(f"LEAK: {tk} as-of {as_of} tapi data terakhir {used[-1]['date']} -- BATAL.")
                if checked < 3:
                    m = re.search(r"Current Price:\s*Rp\s*([\d.,]+)", res.get("details") or "")
                    if m:
                        val = float(m.group(1).replace(",", ""))
                        if abs(val - price) > max(1.0, price * 0.005):
                            raise RuntimeError(f"HARGA: details={val} != close as-of {price} ({tk} {as_of}) -- BATAL.")
                    checked += 1
                hist = rows[:i + 1]
                atr, ma50v = atr14(hist), sma_close(hist, 50)
                sup, rs, bs, br = sys_levels(res, price)
                ssup, srs = swing_levels(hist, price)
                raw["n"] += 1
                raw["s"] += 1 if bs else 0
                raw["r"] += 1 if br else 0
                if sup:
                    lvls["VP"].add("S", (price - sup[0]) / price, eval_support(fut, sup[0]))
                if rs:
                    lvls["VP"].add("R", (rs[0] - price) / price, eval_resistance(fut, rs[0]))
                if ssup:
                    lvls["SWING"].add("S", (price - ssup[0]) / price, eval_support(fut, ssup[0]))
                if srs:
                    lvls["SWING"].add("R", (srs[0] - price) / price, eval_resistance(fut, srs[0]))
                for stop, filt in CFGS:
                    for m, (su, _) in (("VP", (sup, rs)), ("SWING", (ssup, srs))):
                        s1 = su[0] if su else None
                        s2 = su[1] if len(su) > 1 else None
                        sl = stop_for(stop, s1, s2, atr) if s1 else None
                        if stop == "s2" and s2 is None:
                            sl = None
                        trade_signal(loc.setdefault((m, stop, filt), Acc()), fut, price, s1, sl, ma50v, filt, regime)
                    if stop == "s2":
                        e = price * (1 - UD)
                        trade_signal(loc.setdefault(("UNIFORM", stop, filt), Acc()), fut, price, e, e * (1 - UR), ma50v, filt, regime)
            for k, a in loc.items():
                accs.setdefault(k, Acc()).merge(a)
            per.append((tk, loc))
            print(f"selesai {tk}")
    finally:
        _unpatch_all()

    print("\n" + "=" * 78)
    print(f"PARAMETER: step={STEP} fill={FILL} hold={HOLD} rr={RR} k={ATRK} fee={FEE * 100:.2f}% start={START} | ticker={len(per)}")
    print("EXP = expectancy kotor (R); NET = setelah biaya round-trip; UNIFORM = beli x% di bawah harga tanpa struktur level")
    summary_table(accs, CFGS)
    print(f"\nKualitas level mentah sistem: sampel {raw['n']} | S1 >= harga: {pct(raw['s'], raw['n']).strip()} | R1 <= harga: {pct(raw['r'], raw['n']).strip()} | gagal: {raw['fail']}")

    print("\n" + "=" * 78)
    print("BREAKDOWN PER REZIM PASAR IHSG (dihitung dari MA50/MA200 harga ^JKSE, bukan tabel IHSG Signal)")
    for reg in ("Bullish", "Sideways", "Bearish"):
        n_trades = sum(1 for a in accs.values() for t in a.trades if t.get("regime") == reg)
        summary_table(accs, CFGS, regime_filter=reg, label=f"REZIM: {reg} (total trade tersimulasi: {n_trades})")
        if n_trades < 80:
            print(f"  >> PERINGATAN: sampel {reg} cuma {n_trades} trade -- terlalu kecil untuk disimpulkan apa pun.")
    if not BRIEF:
        for m in ("VP", "SWING"):
            a = accs.get((m, "s2", "none"))
            if a:
                detail({"VP": "SISTEM (Volume Profile + fallback)", "SWING": "BASELINE swing"}[m], a, lvls[m])
        print("\nPER TICKER (stop=s2, filter=none): trade | exp(R)   VP  vs  swing")
        for tk, loc in per:
            def e(k):
                a = loc.get(k)
                s = stats(a.trades) if a else None
                return f"{s['n']:3d} | {s['exp']:+.2f}" if s else "  0 |   n/a"
            print(f"  {tk:6s} {e(('VP', 's2', 'none'))}     {e(('SWING', 's2', 'none'))}")
    print("\n" + "=" * 78)
    print("DIAGNOSTIK A: VP s2 none vs ma50 saat Bearish -- breakdown per ticker")
    for combo_label, key in (("VP s2 none", ("VP", "s2", "none")), ("VP s2 ma50", ("VP", "s2", "ma50"))):
        print(f"\n-- {combo_label} (regime=Bearish) --")
        for tk, loc in per:
            a = loc.get(key)
            if not a:
                continue
            tt = [t for t in a.trades if t.get("regime") == "Bearish"]
            s = stats(tt)
            if s:
                print(f"  {tk:6s} n={s['n']:3d} win={s['win']:.0f}% exp={s['exp']:+.2f}R")

    print("\n" + "=" * 78)
    print("DIAGNOSTIK B: Episode rezim Bearish (rentang tanggal kontinu)")
    ep_start, prev = None, None
    for d, r in zip(ihsg_dates, ihsg_regimes):
        if r == "Bearish":
            if ep_start is None:
                ep_start = d
            prev = d
        else:
            if ep_start is not None:
                print(f"  {ep_start} s/d {prev}")
                ep_start = None
    if ep_start is not None:
        print(f"  {ep_start} s/d {prev}")

    print("\nCATATAN: sampel kecil, jendela saling tumpang tindih, dan data hanya ~1 tahun (hasil sangat bergantung rezim pasar);")
    print("selisih < ~0.15R antar varian tidak bisa dibedakan dari kebetulan.")


main()
