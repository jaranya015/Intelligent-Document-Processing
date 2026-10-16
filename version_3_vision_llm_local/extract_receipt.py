"""
extract_receipt.py

ตัวเลือก backend สำหรับสกัดข้อมูล (รูปภาพ/ข้อความ -> JSON)
รองรับ:
    EXTRACTION_BACKEND=gemini    # ใช้ Google Gemini
    EXTRACTION_BACKEND=local     # ใช้ Ollama บนเครื่อง
    EXTRACTION_BACKEND=florence  # ใช้ Microsoft Florence-2 + Regex บนเครื่อง
"""

import config

backend = config.EXTRACTION_BACKEND

if backend == "florence":
    from extract_receipt_florence import (
        extract_with_florence2,
        extract_with_regex,
    )
    
    def extract_receipt_data(image_path: str) -> dict:
        # 1. อ่านข้อความดิบด้วย Florence-2
        raw_text = extract_with_florence2(image_path)
        # 2. สกัดข้อมูลด้วย Regex
        parsed = extract_with_regex(raw_text)
        
        # 3. จัดรูปให้ตรงกับโครงสร้าง JSON ที่ Excel และ Line Flex ต้องการ
        total_val = float(parsed.get("total_amount") or 0.0)
        return {
            "company": parsed.get("customer_name") or "ร้านค้าทั่วไป",
            "document_type": parsed.get("document_type") or "Invoice",
            "document_no": parsed.get("invoice_number") or "-",
            "date": parsed.get("date") or "-",
            "tax_id": None,
            "items": [
                {
                    "name": "รายการสินค้าจากใบเสร็จ",
                    "qty": 1.0,
                    "unit_price": total_val,
                    "amount": total_val
                }
            ],
            "subtotal": total_val,
            "discount": 0.0,
            "vat": 0.0,
            "total": total_val,
            "currency": "THB",
            "low_confidence_fields": []
        }

    def extract_text_to_json(user_text: str) -> dict:
        # Fallback สำหรับข้อความตัวอักษรทั่วไป
        return {
            "customer_name": None,
            "item_name": user_text,
            "qty": 1,
            "unit_price": 0.0,
            "amount": 0.0
        }

elif backend == "local":
    from extract_receipt_local import (  # noqa: F401
        extract_receipt_data,
        extract_text_to_json,
    )
else:
    from extract_receipt_gemini import (  # noqa: F401
        extract_receipt_data,
        extract_text_to_json,
    )