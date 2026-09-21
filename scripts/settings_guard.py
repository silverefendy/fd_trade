"""Jaga Trading Account Settings selama test.
%run /tmp/settings_guard.py snapshot   -> simpan nilai sekarang
%run /tmp/settings_guard.py compare    -> tampilkan perbedaan (default)
%run /tmp/settings_guard.py restore    -> kembalikan field ANGKA yang berubah
"""
import sys
import json
import frappe

MODE = sys.argv[1] if len(sys.argv) > 1 else "compare"
PATH = "/tmp/settings_before_tests.json"
SKIP = {"name", "owner", "modified_by", "creation", "modified", "doctype", "idx", "docstatus"}

d = frappe.get_single("Trading Account Settings").as_dict()
now = {k: v for k, v in d.items() if k not in SKIP and (v is None or isinstance(v, (int, float, str)))}

if MODE == "snapshot":
    json.dump(now, open(PATH, "w"), indent=1)
    print(f"snapshot tersimpan: {len(now)} field -> {PATH}")
else:
    before = json.load(open(PATH))
    diff = {k: (before[k], now.get(k)) for k in before if before[k] != now.get(k)}
    if not diff:
        print("Tidak ada perubahan pada Trading Account Settings. Aman.")
    for k, (a, b) in diff.items():
        print(f"BERUBAH {k}: {a!r} -> {b!r}")
    if MODE == "restore":
        for k, (a, b) in diff.items():
            if isinstance(a, (int, float)):
                frappe.db.set_single_value("Trading Account Settings", k, a)
                print(f"  dikembalikan {k} = {a}")
        frappe.db.commit()
