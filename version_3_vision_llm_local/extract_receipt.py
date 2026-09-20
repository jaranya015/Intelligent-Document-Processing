"""
extract_receipt.py

ตัวเลือก backend สำหรับสกัดข้อมูล (รูปภาพ/ข้อความ -> JSON)
ไม่ต้องแก้โค้ดตรงไหนเพื่อสลับ ให้แก้ค่าใน .env แทน:

    EXTRACTION_BACKEND=gemini   # ค่า default - ใช้ Google Gemini (ฟรีตามโควตา, ต้องมีเน็ต, แม่นยำกว่า)
    EXTRACTION_BACKEND=local    # ใช้ Ollama บนเครื่อง (ไม่ต้องมีเน็ต, แม่นยำน้อยกว่า)

main.py ให้ import จากไฟล์นี้ไฟล์เดียว:
    from version_3_vision_llm_local.extract_receipt import extract_receipt_data, extract_text_to_json
"""

from version_3_vision_llm_local import config

if config.EXTRACTION_BACKEND == "local":
    from version_3_vision_llm_local.extract_receipt_local import (  # noqa: F401
        extract_receipt_data,
        extract_text_to_json,
    )
else:
    from version_3_vision_llm_local.extract_receipt_gemini import (  # noqa: F401
        extract_receipt_data,
        extract_text_to_json,
    )