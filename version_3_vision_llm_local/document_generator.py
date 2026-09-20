"""
document_generator.py
วาดข้อความลงบน template รูปภาพ (1414 x 2000 px)

พิกัดทั้งหมดวัดมาจากไฟล์ templates/invoice_template.jpg โดยตรง
และใช้ "เส้นฐานตัวอักษร (baseline)" เป็นตัวอ้างอิง ไม่ใช่มุมบนซ้าย
จึงทำให้ข้อความนั่งตรงบรรทัดของ template พอดี ไม่ว่าจะเปลี่ยนขนาดฟอนต์

ถ้าต้องขยับช่องไหน ให้แก้เฉพาะค่าใน FIELDS / TABLE / SUMMARY ด้านล่าง
(ดูตำแหน่งจริงได้ด้วย  python test_doc.py invoice --grid --debug)
"""

from pathlib import Path
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

# ขนาด template มาตรฐานที่ใช้วัดพิกัด ถ้าไฟล์จริงขนาดต่างจากนี้ จะถูกปรับให้เท่ากันก่อนวาด
DESIGN_W, DESIGN_H = 1414, 2000

# 🏢 ข้อมูลผู้ออกเอกสาร
MY_COMPANY = {
    "name": "บริษัท pixxie woman จำกัด",
    "address": "หาดใหญ่ สงขลา 90110",
    "tax_id": "1234567890123",
    "phone": "084-2329-514",
    "email": "faiijaran0159@gmail.com",
    "bank_name": "กสิกรไทย (KBANK)",
    "bank_account": "1234-5-67890-1",
}

# ---------------------------------------------------------------------------
# ตำแหน่งช่องกรอก  (x, baseline_y, align, style, max_width)
#   align : "l" ชิดซ้าย | "r" ชิดขวา | "c" กึ่งกลาง
#   style : ชื่อฟอนต์ใน FONT_SIZES
#   max_width : ความกว้างสูงสุดของช่อง (px) เกินจะย่อฟอนต์/ตัดท้ายให้อัตโนมัติ
# ---------------------------------------------------------------------------
FIELDS = {
    # ---- ฝั่งลูกค้า (ซ้ายบน) : baseline 350 / 389 / 428 / 467 ----
    "customer_name":     (230, 350, "l", "main",  700),
    "customer_address":  (230, 389, "l", "small", 700),
    "customer_tax_id":   (230, 428, "l", "small", 230),
    "customer_contact":  (230, 467, "l", "small", 230),
    "customer_email":    (615, 428, "l", "small", 320),
    "customer_phone":    (615, 467, "l", "small", 320),

    # ---- ข้อมูลเอกสาร (ขวาบน) ----
    "doc_no":            (1075, 350, "l", "small", 245),
    "doc_date":          (1075, 389, "l", "main", 240),
    "due_date":          (1075, 428, "l", "main", 240),
    "reference":         (1075, 467, "l", "main", 240),

    # ---- ฝั่งผู้ออกเอกสาร : baseline 552 / 591 / 630 ----
    "my_name":           (230, 552, "l", "small", 470),
    "my_address":        (230, 591, "l", "small", 470),
    "my_tax_id":         (925, 552, "l", "small", 380),
    "my_phone":          (925, 591, "l", "small", 380),
    "my_email":          (925, 630, "l", "small", 380),

    # ---- ท้ายเอกสาร ----
    "bank_name":         (230, 1589, "l", "small", 600),
    "bank_account":      (230, 1628, "l", "small", 600),
}

# ---- ตารางรายการสินค้า ----
TABLE = {
    "top": 718,            # เส้นใต้หัวตาราง
    "bottom": 1172,        # เส้นปิดตาราง
    "first_baseline": 760,
    "row_height": 45,
    "col_no": 131,         # ลำดับ (กึ่งกลาง)
    "col_name": 200,       # รายการสินค้า (ชิดซ้าย)
    "col_name_width": 620,
    "col_qty": 881,        # จำนวน (กึ่งกลาง)
    "col_price": 1084,     # ราคา/หน่วย (ชิดขวา)
    "col_amount": 1290,    # ราคารวม (ชิดขวา)
}

# ---- สรุปยอด / หมายเหตุ / เงื่อนไข ----
SUMMARY = {
    "subtotal": (1290, 1219, "r", "main"),
    "vat":      (1290, 1258, "r", "main"),
    "discount": (1290, 1297, "r", "main"),
    "total":    (1290, 1409, "r", "bold"),
    "note_x": 116, "note_baseline": 1262, "note_width": 660, "note_lines": 2,
    "terms_x": 102, "terms_baseline": 1772, "terms_width": 700, "terms_lines": 4,
}

LINE_GAP = 39  # ระยะห่างบรรทัดมาตรฐานของ template

FONT_SIZES = {"main": 38, "small": 34, "bold": 44}

_ANCHOR = {"l": "ls", "r": "rs", "c": "ms"}

DOC_PREFIX = {"invoice": "INV", "quotation": "QT", "po": "PO", "tax_invoice": "TAX"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _load_fonts():
    font_path = CURRENT_DIR / "THSarabunNew.ttf"
    fonts = {}
    for name, size in FONT_SIZES.items():
        try:
            fonts[name] = ImageFont.truetype(str(font_path), size)
        except Exception:
            try:
                fonts[name] = ImageFont.truetype(
                    "/System/Library/Fonts/Supplemental/Thonburi.ttc", int(size * 0.8))
            except Exception:
                fonts[name] = ImageFont.load_default()
    return fonts


def _text_width(draw, text, font):
    return draw.textlength(str(text), font=font)


def _fit_font(draw, text, font, max_width, min_ratio=0.75):
    """ย่อฟอนต์ลงถ้าข้อความยาวเกินช่อง ถ้ายังไม่พอก็ตัดท้ายแล้วใส่ …"""
    text = str(text)
    if not max_width or _text_width(draw, text, font) <= max_width:
        return font, text

    base_size = font.size
    for size in range(base_size - 1, int(base_size * min_ratio) - 1, -1):
        try:
            f = font.font_variant(size=size)
        except Exception:
            break
        if _text_width(draw, text, f) <= max_width:
            return f, text

    try:
        f = font.font_variant(size=max(12, int(base_size * min_ratio)))
    except Exception:
        f = font
    s = text
    while s and _text_width(draw, s + "…", f) > max_width:
        s = s[:-1]
    return f, (s + "…") if s else ""


def _wrap(draw, text, font, max_width, max_lines):
    """ตัดบรรทัดข้อความยาว (ตัดตามช่องว่างก่อน ถ้าไม่ได้ค่อยตัดตามตัวอักษร)"""
    lines, current = [], ""
    for word in str(text).replace("\n", " \n ").split(" "):
        if word == "\n":
            if current:
                lines.append(current)
            current = ""
            continue
        if not word:
            continue
        trial = (current + " " + word).strip() if current else word
        if _text_width(draw, trial, font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
                current = ""
            while _text_width(draw, word, font) > max_width and len(word) > 1:
                cut = len(word)
                while cut > 1 and _text_width(draw, word[:cut], font) > max_width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return [l for l in lines if l][:max_lines]


def _draw_field(draw, fonts, key, value, color="#111111", debug=False):
    if key not in FIELDS:
        return
    x, y, align, style, max_w = FIELDS[key]
    text = "-" if value in (None, "") else str(value)
    font, text = _fit_font(draw, text, fonts[style], max_w)
    draw.text((x, y), text, font=font, fill=color, anchor=_ANCHOR[align])
    if debug:
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill="red")
        draw.line([(x, y + 2), (x + max_w, y + 2)], fill=(255, 120, 120), width=1)


def _money(v):
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _fmt_qty(q):
    q = float(q)
    return f"{q:,.0f}" if q.is_integer() else f"{q:,.2f}"


def _normalize_items(data: dict):
    """รองรับทั้ง items=[{...}] และรายการเดียว (item_name/qty/unit_price/amount)"""
    items = data.get("items")
    if isinstance(items, list) and items:
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = it.get("name") or it.get("item_name") or it.get("item") or "-"
            try:
                qty = float(it.get("qty") or 1)
            except (TypeError, ValueError):
                qty = 1.0
            try:
                price = float(it.get("unit_price") or 0)
            except (TypeError, ValueError):
                price = 0.0
            try:
                amount = float(it.get("amount") or (qty * price))
            except (TypeError, ValueError):
                amount = qty * price
            out.append({"name": name, "qty": qty, "unit_price": price, "amount": amount})
        if out:
            return out

    name = data.get("item_name") or data.get("item") or "รายการสินค้า"
    try:
        qty = float(data.get("qty") or 1)
    except (TypeError, ValueError):
        qty = 1.0
    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    try:
        price = float(data.get("unit_price") or (amount / qty if qty else amount))
    except (TypeError, ValueError):
        price = amount
    return [{"name": name, "qty": qty, "unit_price": price, "amount": amount}]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def generate_document_image(doc_type: str, data: dict, template_filename: str,
                            output_filename: str, debug: bool = False) -> str:
    template_path = BASE_DIR / "templates" / template_filename
    if not template_path.exists() or template_path.stat().st_size == 0:
        raise FileNotFoundError(
            f"ไม่พบไฟล์ template ที่ใช้งานได้: {template_path} "
            f"(ตอนนี้มีเฉพาะ invoice_template.jpg และ quotation_template.jpg)")

    output_dir = BASE_DIR / "static" / "generated_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    img = Image.open(template_path).convert("RGB")
    if img.size != (DESIGN_W, DESIGN_H):
        img = img.resize((DESIGN_W, DESIGN_H), Image.LANCZOS)

    draw = ImageDraw.Draw(img)
    fonts = _load_fonts()
    black = "#111111"

    # ---------- 1) ลูกค้า ----------
    for key in ("customer_name", "customer_address", "customer_tax_id",
                "customer_contact", "customer_email", "customer_phone"):
        _draw_field(draw, fonts, key, data.get(key), black, debug)

    # ---------- 2) ข้อมูลเอกสาร ----------
    now = datetime.now()
    try:
        credit_days = int(float(data.get("credit_term") or 0))
    except (TypeError, ValueError):
        credit_days = 0

    doc_no = data.get("doc_no") or f"{DOC_PREFIX.get(doc_type, 'DOC')}-{now.strftime('%Y%m%d%H%M')}"
    doc_date = data.get("doc_date") or now.strftime("%d/%m/%Y")
    due_date = data.get("due_date") or (
        (now + timedelta(days=credit_days)).strftime("%d/%m/%Y") if credit_days > 0 else "-")
    reference = data.get("reference") or (f"เครดิต {credit_days} วัน" if credit_days > 0 else "-")

    _draw_field(draw, fonts, "doc_no", doc_no, black, debug)
    _draw_field(draw, fonts, "doc_date", doc_date, black, debug)
    _draw_field(draw, fonts, "due_date", due_date, black, debug)
    _draw_field(draw, fonts, "reference", reference, black, debug)

    # ---------- 3) ผู้ออกเอกสาร ----------
    _draw_field(draw, fonts, "my_name", MY_COMPANY["name"], black, debug)
    _draw_field(draw, fonts, "my_address", MY_COMPANY["address"], black, debug)
    _draw_field(draw, fonts, "my_tax_id", MY_COMPANY["tax_id"], black, debug)
    _draw_field(draw, fonts, "my_phone", MY_COMPANY["phone"], black, debug)
    _draw_field(draw, fonts, "my_email", MY_COMPANY["email"], black, debug)

    # ---------- 4) ตารางสินค้า ----------
    items = _normalize_items(data)
    max_rows = int((TABLE["bottom"] - TABLE["first_baseline"]) // TABLE["row_height"]) + 1
    overflow = len(items) - max_rows
    if overflow > 0:
        items = items[:max_rows - 1]

    for i, it in enumerate(items):
        y = TABLE["first_baseline"] + i * TABLE["row_height"]
        draw.text((TABLE["col_no"], y), str(i + 1), font=fonts["main"], fill=black, anchor="ms")
        name_font, name_text = _fit_font(draw, it["name"], fonts["main"], TABLE["col_name_width"])
        draw.text((TABLE["col_name"], y), name_text, font=name_font, fill=black, anchor="ls")
        draw.text((TABLE["col_qty"], y), _fmt_qty(it["qty"]), font=fonts["main"], fill=black, anchor="ms")
        draw.text((TABLE["col_price"], y), _money(it["unit_price"]), font=fonts["main"], fill=black, anchor="rs")
        draw.text((TABLE["col_amount"], y), _money(it["amount"]), font=fonts["main"], fill=black, anchor="rs")
        if debug:
            draw.ellipse([TABLE["col_name"] - 3, y - 3, TABLE["col_name"] + 3, y + 3], fill="red")

    if overflow > 0:
        y = TABLE["first_baseline"] + (max_rows - 1) * TABLE["row_height"]
        draw.text((TABLE["col_name"], y), f"… และอีก {overflow + 1} รายการ",
                  font=fonts["main"], fill=black, anchor="ls")

    # ---------- 5) สรุปยอด ----------
    raw_subtotal = data.get("subtotal")
    subtotal = float(raw_subtotal) if raw_subtotal not in (None, "") else sum(i["amount"] for i in items)
    try:
        discount = float(data.get("discount") or 0)
    except (TypeError, ValueError):
        discount = 0.0
    if data.get("vat") in (None, ""):
        vat = round((subtotal - discount) * 0.07, 2) if data.get("include_vat", True) else 0.0
    else:
        try:
            vat = float(data.get("vat"))
        except (TypeError, ValueError):
            vat = 0.0
    raw_total = data.get("total")
    total = float(raw_total) if raw_total not in (None, "") else subtotal - discount + vat

    for key, val in (("subtotal", subtotal), ("vat", vat), ("discount", discount), ("total", total)):
        x, y, align, style = SUMMARY[key]
        draw.text((x, y), _money(val), font=fonts[style], fill=black, anchor=_ANCHOR[align])
        if debug:
            draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill="red")

    # ---------- 6) หมายเหตุ / เงื่อนไข / บัญชี ----------
    if data.get("note"):
        for n, line in enumerate(_wrap(draw, data["note"], fonts["small"],
                                       SUMMARY["note_width"], SUMMARY["note_lines"])):
            draw.text((SUMMARY["note_x"], SUMMARY["note_baseline"] + n * LINE_GAP),
                      line, font=fonts["small"], fill=black, anchor="ls")

    if data.get("terms"):
        for n, line in enumerate(_wrap(draw, data["terms"], fonts["small"],
                                       SUMMARY["terms_width"], SUMMARY["terms_lines"])):
            draw.text((SUMMARY["terms_x"], SUMMARY["terms_baseline"] + n * LINE_GAP),
                      line, font=fonts["small"], fill=black, anchor="ls")

    _draw_field(draw, fonts, "bank_name", MY_COMPANY["bank_name"], black, debug)
    _draw_field(draw, fonts, "bank_account", MY_COMPANY["bank_account"], black, debug)

    img.save(output_path, "JPEG", quality=95)
    return str(output_path)


def draw_grid(image_path: str, step: int = 50) -> str:
    """วาดเส้นตารางพิกัดทับรูป ไว้ดูว่าต้องขยับกี่ px"""
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(str(CURRENT_DIR / "THSarabunNew.ttf"), 24)
    except Exception:
        f = ImageFont.load_default()

    w, h = img.size
    for x in range(0, w, step):
        big = x % (step * 2) == 0
        draw.line([(x, 0), (x, h)], fill=(255, 0, 0) if big else (255, 195, 195), width=1)
        if big:
            draw.text((x + 2, 2), str(x), fill=(200, 0, 0), font=f)
    for y in range(0, h, step):
        big = y % (step * 2) == 0
        draw.line([(0, y), (w, y)], fill=(0, 0, 255) if big else (195, 195, 255), width=1)
        if big:
            draw.text((2, y + 2), str(y), fill=(0, 0, 200), font=f)

    out = str(Path(image_path).with_name(Path(image_path).stem + "_grid.jpg"))
    img.save(out, "JPEG", quality=92)
    return out