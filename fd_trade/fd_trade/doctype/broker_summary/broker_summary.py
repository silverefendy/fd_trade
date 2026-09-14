"""
Broker Summary Controller
Stores daily broker transaction summary (bandarmologi) per ticker with Excel import.
"""

import frappe
from frappe.model.document import Document
from frappe import _
import openpyxl
from openpyxl import load_workbook


class BrokerSummary(Document):
"""Broker Summary entry for tracking broker flow data."""

def on_update(self):
"""Generate insight notes after successful import."""
self.generate_insight_notes()

def generate_insight_notes(self):
"""Auto-generate insight notes based on broker flow data."""
if not self.avg_pct:
return

insight = ""

if self.avg_pct <= -15:
insight = "BIG DISTRIBUTION -- broker besar net JUAL signifikan"
elif self.avg_pct >= 15:
insight = "BIG ACCUMULATION -- broker besar net BELI signifikan"
else:
insight = "Netral / tidak ada distribusi atau akumulasi signifikan"

# Compare price to average price
if self.price and self.average_price:
if self.price < self.average_price:
insight += "\\nHarga saat ini di bawah rata-rata broker (Rp" + str(self.average_price) + ")"
elif self.price > self.average_price:
insight += "\\nHarga saat ini di atas rata-rata broker (Rp" + str(self.average_price) + ")"

self.insight_notes = insight


@frappe.whitelist()
def import_from_excel(docname, file_url, ticker):
"""Import broker summary data from Excel file."""
import os

doc = frappe.get_doc("Broker Summary", docname)

# Get file path from file URL
file_path = frappe.get_site_path(frappe.utils.get_url_path(file_url).lstrip("/"))

if not os.path.exists(file_path):
frappe.throw(_("File not found: {0}").format(file_path))

try:
wb = load_workbook(file_path, data_only=True)
ws = wb.active

warnings = []
imported_count = 0

# Read fixed cell positions
doc.date = ws["B7"].value
doc.top1_volume = parse_excel_value(ws["B9"].value)
doc.top1_pct = parse_excel_value(ws["C9"].value)
doc.top3_volume = parse_excel_value(ws["B10"].value)
doc.top3_pct = parse_excel_value(ws["C10"].value)
doc.top5_volume = parse_excel_value(ws["B11"].value)
doc.top5_pct = parse_excel_value(ws["C11"].value)
doc.avg_volume = parse_excel_value(ws["B12"].value)
doc.avg_pct = parse_excel_value(ws["C12"].value)
doc.avg_dist_label = ws["E12"].value
doc.buyer_count = parse_excel_value(ws["B15"].value)
doc.seller_count = parse_excel_value(ws["C15"].value)
doc.net_volume = parse_excel_value(ws["B16"].value)
doc.net_value = parse_excel_value(ws["B17"].value)
doc.average_price = parse_excel_value(ws["B18"].value)

# Clear existing broker details
doc.broker_details = []

# Read broker detail rows starting from row 20
row_num = 20
while True:
if ws[f"A{row_num}"].value is None or str(ws[f"A{row_num}"].value).strip() == "":
break

try:
buy_broker = ws[f"A{row_num}"].value
buy_value = parse_excel_value(ws[f"B{row_num}"].value)
buy_lot = parse_excel_value(ws[f"C{row_num}"].value)
buy_freq = parse_excel_value(ws[f"D{row_num}"].value)
buy_avg_price = parse_excel_value(ws[f"E{row_num}"].value)

sell_broker = ws[f"F{row_num}"].value
sell_value = parse_excel_value(ws[f"G{row_num}"].value)
sell_lot = parse_excel_value(ws[f"H{row_num}"].value)
sell_freq = parse_excel_value(ws[f"I{row_num}"].value)
sell_avg_price = parse_excel_value(ws[f"J{row_num}"].value)

# Add buy side if broker exists
if buy_broker and str(buy_broker).strip() != "-":
doc.append("broker_details", {
"broker_code": str(buy_broker),
"side": "Buy",
"value_rp": buy_value,
"lot": buy_lot,
"freq": buy_freq,
"avg_price": buy_avg_price
})
imported_count += 1

# Add sell side if broker exists
if sell_broker and str(sell_broker).strip() != "-":
doc.append("broker_details", {
"broker_code": str(sell_broker),
"side": "Sell",
"value_rp": sell_value,
"lot": sell_lot,
"freq": sell_freq,
"avg_price": sell_avg_price
})
imported_count += 1

row_num += 1

except Exception as e:
warnings.append(f"Row {row_num}: {str(e)}")
row_num += 1
continue

doc.save()

# Show summary
message = f"Imported {imported_count} broker rows successfully."
if warnings:
message += f" {len(warnings)} rows skipped due to format issues."

frappe.msgprint(message)
return {"success": True, "imported": imported_count, "skipped": len(warnings)}

except Exception as e:
frappe.throw(_("Excel import failed: {0}").format(str(e)))


def parse_excel_value(value):
"""Parse Excel cell value handling various formats (B, M, K suffixes, commas)."""
if value is None:
return None

# If already a number, return as is
if isinstance(value, (int, float)):
return float(value)

# Convert to string and process
value_str = str(value).strip()

# Remove commas
value_str = value_str.replace(",", "")

# Handle suffixes
if value_str.endswith("B"):
return float(value_str[:-1]) * 1000000000
elif value_str.endswith("M"):
return float(value_str[:-1]) * 1000000
elif value_str.endswith("K"):
return float(value_str[:-1]) * 1000
else:
try:
return float(value_str)
except ValueError:
return None
