"""
invoice_generator.py
====================
Generate professional PDF invoices from Python dicts or JSON files.

Usage:
    python invoice_generator.py                  # generates sample invoice
    python invoice_generator.py my_invoice.json  # generates from JSON file
"""

import sys
import json
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


# ── Colour palette ─────────────────────────────────────────────────────────
INK        = colors.HexColor("#1a1612")
RUST       = colors.HexColor("#b84a2e")
GOLD       = colors.HexColor("#c9963a")
CREAM      = colors.HexColor("#f5f0e8")
MUTED      = colors.HexColor("#8a7f72")
BORDER     = colors.HexColor("#ddd5c4")
ROW_ALT    = colors.HexColor("#faf7f2")
WHITE      = colors.white


def draw_invoice(data: dict, output_path: str = "invoice.pdf"):
    """
    Render a PDF invoice from a data dictionary.

    Required keys:
        business        – dict: name, address, email, phone
        client          – dict: name, address, email
        invoice_number  – str
        items           – list of dicts: description, qty, unit_price

    Optional keys:
        issue_date      – "YYYY-MM-DD"  (defaults to today)
        due_date        – "YYYY-MM-DD"  (defaults to issue_date + 14 days)
        currency        – str           (defaults to "KES")
        tax_rate        – float         (defaults to 0.16 for 16% VAT)
        notes           – str
        paid            – bool          (stamp PAID if True)
    """
    W, H = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # ── Helpers ────────────────────────────────────────────────────────────
    def text(x, y, s, size=10, color=INK, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawString(x, y, str(s))

    def rtext(x, y, s, size=10, color=INK, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawRightString(x, y, str(s))

    def hrule(y, x1=20*mm, x2=W - 20*mm, color=BORDER, width=0.5):
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x1, y, x2, y)

    def fmt(amount):
        return f"{currency} {amount:,.2f}"

    # ── Pull data ──────────────────────────────────────────────────────────
    biz     = data["business"]
    client  = data["client"]
    inv_no  = data.get("invoice_number", "INV-001")
    items   = data.get("items", [])
    currency= data.get("currency", "KES")
    tax_rate= data.get("tax_rate", 0.16)
    notes   = data.get("notes", "")
    paid    = data.get("paid", False)

    today   = datetime.today()
    issue   = datetime.strptime(data["issue_date"], "%Y-%m-%d") \
                if "issue_date" in data else today
    due     = datetime.strptime(data["due_date"], "%Y-%m-%d") \
                if "due_date" in data else issue + timedelta(days=14)

    # ── Header bar ────────────────────────────────────────────────────────
    c.setFillColor(INK)
    c.rect(0, H - 36*mm, W, 36*mm, fill=1, stroke=0)

    # Business name
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(WHITE)
    c.drawString(20*mm, H - 18*mm, biz["name"])

    # INVOICE label
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#ffffff60"))
    c.drawRightString(W - 20*mm, H - 14*mm, "INVOICE")
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(GOLD)
    c.drawRightString(W - 20*mm, H - 22*mm, inv_no)

    # Rust accent stripe
    c.setFillColor(RUST)
    c.rect(0, H - 38*mm, W, 2*mm, fill=1, stroke=0)

    # ── Business details ──────────────────────────────────────────────────
    y = H - 50*mm
    for line in [biz.get("address",""), biz.get("email",""), biz.get("phone","")]:
        if line:
            text(20*mm, y, line, size=8, color=MUTED)
            y -= 5*mm

    # ── Invoice meta ──────────────────────────────────────────────────────
    meta_x = W - 80*mm
    meta_labels = [
        ("Issue Date",  issue.strftime("%d %b %Y")),
        ("Due Date",    due.strftime("%d %b %Y")),
        ("Currency",    currency),
    ]
    y_meta = H - 50*mm
    for label, value in meta_labels:
        text(meta_x, y_meta, label, size=8, color=MUTED)
        rtext(W - 20*mm, y_meta, value, size=8, bold=True)
        y_meta -= 5*mm

    # ── Bill To ───────────────────────────────────────────────────────────
    y = H - 85*mm
    text(20*mm, y, "BILL TO", size=8, color=RUST, bold=True)
    y -= 6*mm
    text(20*mm, y, client["name"], size=11, bold=True)
    y -= 5*mm
    for line in [client.get("address",""), client.get("email","")]:
        if line:
            text(20*mm, y, line, size=9, color=MUTED)
            y -= 5*mm

    # ── Items table ───────────────────────────────────────────────────────
    table_top = H - 120*mm
    col = {
        "desc":  20*mm,
        "qty":   W - 80*mm,
        "rate":  W - 55*mm,
        "total": W - 20*mm,
    }
    row_h = 9*mm

    # Table header
    c.setFillColor(INK)
    c.rect(20*mm, table_top - 8*mm, W - 40*mm, 8*mm, fill=1, stroke=0)
    headers = [
        (col["desc"],  "DESCRIPTION", False),
        (col["qty"],   "QTY",         True),
        (col["rate"],  "UNIT PRICE",  True),
        (col["total"], "TOTAL",       True),
    ]
    for x, label, right in headers:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(CREAM)
        if right:
            c.drawRightString(x, table_top - 5.5*mm, label)
        else:
            c.drawString(x, table_top - 5.5*mm, label)

    # Rows
    subtotal = 0
    y_row = table_top - 8*mm
    for i, item in enumerate(items):
        qty        = float(item.get("qty", 1))
        unit_price = float(item["unit_price"])
        line_total = qty * unit_price
        subtotal  += line_total
        row_y      = y_row - row_h

        # Alternating background
        bg = ROW_ALT if i % 2 == 0 else WHITE
        c.setFillColor(bg)
        c.rect(20*mm, row_y, W - 40*mm, row_h, fill=1, stroke=0)

        mid = row_y + 3*mm
        text(col["desc"], mid, item["description"], size=9)
        rtext(col["qty"],   mid, f"{qty:.0f}",        size=9)
        rtext(col["rate"],  mid, fmt(unit_price),      size=9)
        rtext(col["total"], mid, fmt(line_total),      size=9, bold=True)

        y_row = row_y

    # Bottom border of table
    hrule(y_row, color=BORDER)

    # ── Totals ────────────────────────────────────────────────────────────
    tax    = subtotal * tax_rate
    total  = subtotal + tax
    ty     = y_row - 8*mm

    def total_row(label, value, highlight=False):
        nonlocal ty
        if highlight:
            c.setFillColor(INK)
            c.rect(W - 80*mm, ty - 2*mm, 60*mm, 8*mm, fill=1, stroke=0)
            rtext(W - 45*mm, ty + 0.5*mm, label, size=9, color=CREAM)
            rtext(W - 20*mm, ty + 0.5*mm, value, size=10, color=GOLD, bold=True)
        else:
            rtext(W - 45*mm, ty, label, size=9, color=MUTED)
            rtext(W - 20*mm, ty, value, size=9)
        ty -= 8*mm

    total_row("Subtotal",              fmt(subtotal))
    total_row(f"Tax ({tax_rate*100:.0f}% VAT)", fmt(tax))
    total_row("TOTAL DUE",             fmt(total), highlight=True)

    # ── PAID stamp ────────────────────────────────────────────────────────
    if paid:
        c.saveState()
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.setFont("Helvetica-Bold", 72)
        c.setFillColor(colors.HexColor("#2dd4a030"))
        c.drawCentredString(0, 0, "PAID")
        c.restoreState()

    # ── Notes ─────────────────────────────────────────────────────────────
    if notes:
        ny = ty - 8*mm
        hrule(ny + 6*mm)
        text(20*mm, ny, "NOTES", size=8, color=RUST, bold=True)
        text(20*mm, ny - 6*mm, notes, size=8, color=MUTED)

    # ── Footer ────────────────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, W, 16*mm, fill=1, stroke=0)
    hrule(16*mm, color=BORDER)
    footer = f"Thank you for your business · {biz.get('email','')} · {biz.get('phone','')}"
    text(20*mm, 6*mm, footer, size=8, color=MUTED)

    c.save()
    print(f"  Invoice saved → {output_path}")
    return output_path


# ── Sample data ────────────────────────────────────────────────────────────
SAMPLE = {
    "business": {
        "name":    "Vin Digital Studio",
        "address": "Westlands, Nairobi, Kenya",
        "email":   "vin@vindigital.co.ke",
        "phone":   "+254 700 000 000",
    },
    "client": {
        "name":    "Savannah Retail Ltd",
        "address": "Karen, Nairobi, Kenya",
        "email":   "accounts@savannah.co.ke",
    },
    "invoice_number": "INV-0042",
    "currency":       "KES",
    "tax_rate":       0.16,
    "notes":          "Payment via M-Pesa Paybill 123456, Account: INV-0042. Thank you!",
    "paid":           False,
    "items": [
        {"description": "Business Website Design & Development", "qty": 1,  "unit_price": 85000},
        {"description": "Monthly Hosting & Maintenance",         "qty": 3,  "unit_price":  8500},
        {"description": "SEO Setup & Google Analytics",          "qty": 1,  "unit_price": 15000},
        {"description": "Logo & Brand Identity Package",         "qty": 1,  "unit_price": 25000},
        {"description": "Social Media Banner Set (10 banners)",  "qty": 1,  "unit_price": 12000},
    ],
}


# ── CLI entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
        out = sys.argv[1].replace(".json", ".pdf")
    else:
        data = SAMPLE
        out  = "invoice_sample.pdf"

    print(f"\n  Generating invoice: {data.get('invoice_number','INV-001')}")
    draw_invoice(data, out)
    print("  Done.\n")
