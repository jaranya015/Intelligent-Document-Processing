"""
test_doc.py

ทดสอบ/จัดตำแหน่งข้อความบน template โดยไม่ต้องใช้ LINE, ngrok, Ollama หรือ .env
ใช้แค่ Pillow + ฟอนต์ THSarabunNew.ttf

วิธีใช้ (รันจากโฟลเดอร์ version_3_vision_llm_local):
    python test_doc.py                    # ทดสอบใบแจ้งหนี้ (invoice)
    python test_doc.py quotation          # ทดสอบใบเสนอราคา
    python test_doc.py invoice --debug    # วาดจุดแดง+ชื่อช่อง ตรงตำแหน่งที่ระบบวาง
    python test_doc.py invoice --grid     # วาดเส้นตารางพิกัดทับ ไว้อ่านค่า x,y
    python test_doc.py invoice --long     # ทดสอบข้อความยาว/หลายรายการ (เช็กการล้น)
    python test_doc.py invoice --open     # เปิดรูปให้เลย (macOS)

ผลลัพธ์อยู่ที่  ../static/generated_docs/test_<doc>.jpg  (และ _grid.jpg ถ้าใช้ --grid)

ขั้นตอนปรับตำแหน่ง:
    1) รัน --grid --debug แล้วดูรูป จดว่าช่องไหนต้องขยับกี่ px
    2) แก้ตัวเลขใน FIELDS / TABLE ของ document_generator.py
    3) รันใหม่ ทำซ้ำจนพอใจ แล้วค่อยกลับไปรันบอท LINE
"""

import argparse
import subprocess
import sys

import document_generator as dg

# ข้อมูลตัวอย่างหน้าตาเหมือนที่ LLM จะสกัดมาจากข้อความใน LINE
SAMPLE_SIMPLE = {
    "customer_name": "บริษัท ตัวอย่างการค้า จำกัด",
    "customer_address": "123 ถ.นิพัทธ์อุทิศ 3 หาดใหญ่ สงขลา 90110",
    "customer_tax_id": "0105551234567",
    "customer_phone": "081-234-5678",
    "customer_email": "buyer@example.com",
    "customer_contact": "คุณสมชาย",
    "item_name": "หมู",
    "qty": 5,
    "unit_price": 100.0,
    "amount": 500.0,
    "credit_term": "15",
}

# แบบหลายรายการ + หมายเหตุ/เงื่อนไข + ข้อความยาว เอาไว้เช็กว่าไม่ล้นช่อง
SAMPLE_LONG = {
    "customer_name": "บริษัท ตัวอย่างการค้าระหว่างประเทศและการขนส่งสินค้าทางทะเล จำกัด (มหาชน)",
    "customer_address": "99/9 หมู่ 1 ต.คอหงส์ อ.หาดใหญ่ จ.สงขลา 90110 ประเทศไทย ตึกสูงใหญ่ชั้น 12",
    "customer_tax_id": "0105551234567",
    "customer_phone": "081-234-5678",
    "customer_email": "purchasing.department@long-company-example.co.th",
    "customer_contact": "คุณสมชาย ใจดีมาก",
    "items": [
        {"name": "หมูสามชั้นสไลด์", "qty": 5, "unit_price": 100.0, "amount": 500.0},
        {"name": "ไข่ไก่เบอร์ 0 (แผง 30 ฟอง)", "qty": 12, "unit_price": 115.5, "amount": 1386.0},
        {"name": "น้ำมันปาล์มบริสุทธิ์ ขนาด 18 ลิตร แบบปี๊บ", "qty": 2, "unit_price": 890.0, "amount": 1780.0},
        {"name": "ข้าวสารหอมมะลิ 100% ถุง 5 กก.", "qty": 20, "unit_price": 165.0, "amount": 3300.0},
        {"name": "ผักกาดขาว", "qty": 1.5, "unit_price": 40.0, "amount": 60.0},
    ],
    "discount": 200.0,
    "vat": 468.72,
    "credit_term": "30",
    "note": "กรุณาจัดส่งภายในวันที่ 30 นี้ ก่อนเวลา 12.00 น. ติดต่อคุณสมชายก่อนเข้าส่งของทุกครั้ง",
    "terms": "1. ชำระเงินภายในกำหนดเครดิต\n2. สินค้าที่ส่งมอบแล้วไม่รับคืน ยกเว้นชำรุดจากการขนส่ง",
}


def main():
    ap = argparse.ArgumentParser(description="ทดสอบวาง template เอกสาร (ไม่ต้องใช้ LINE)")
    ap.add_argument("doc", nargs="?", default="invoice",
                    choices=["invoice", "quotation", "po", "tax_invoice"])
    ap.add_argument("--debug", action="store_true", help="วาดจุดแดง+ชื่อช่อง ตรงตำแหน่งที่วาง")
    ap.add_argument("--grid", action="store_true", help="วาดเส้นตารางพิกัดทับผลลัพธ์")
    ap.add_argument("--long", action="store_true", help="ใช้ข้อมูลยาว/หลายรายการ")
    ap.add_argument("--open", action="store_true", help="เปิดรูปหลังสร้างเสร็จ (macOS/Linux/Windows)")
    args = ap.parse_args()

    data = SAMPLE_LONG if args.long else SAMPLE_SIMPLE
    suffix = ("_long" if args.long else "") + ("_debug" if args.debug else "")
    out_name = f"test_{args.doc}{suffix}.jpg"

    try:
        path = dg.generate_document_image(
            args.doc, data, f"{args.doc}_template.jpg", out_name, debug=args.debug
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    if args.grid:
        path = dg.draw_grid(path)

    print(f"✅ สร้างแล้ว: {path}")

    if args.open:
        if sys.platform == "darwin":
            subprocess.run(["open", path])
        elif sys.platform.startswith("win"):
            import os
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path])


if __name__ == "__main__":
    main()