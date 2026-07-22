"""
batch_process.py

รันสกัดข้อมูลกับรูปใบเสร็จทั้งโฟลเดอร์ในทีเดียว บันทึกผลเป็น:
  - out/<ชื่อไฟล์>.json   (ผลดิบต่อรูป ไว้ตรวจสอบ/debug)
  - out/receipts.xlsx     (รวมทุกรายการเป็นตาราง)

วิธีใช้:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python batch_process.py path/to/photo_for_test_folder
"""

import json
import os
import sys
import time

from extract_receipt_local import extract_receipt_data
from excel_writer import append_receipt_to_excel

VALID_EXT = (".jpg", ".jpeg", ".png", ".webp")


def main(input_folder: str):
    out_dir = os.path.join(input_folder, "..", "vision_llm_output")
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    excel_path = os.path.join(out_dir, "receipts.xlsx")

    files = sorted(
        f for f in os.listdir(input_folder) if f.lower().endswith(VALID_EXT)
    )
    if not files:
        print(f"ไม่พบไฟล์รูปใน {input_folder}")
        return

    print(f"เจอ {len(files)} ไฟล์ เริ่มประมวลผล...")

    ok, failed = 0, 0
    for filename in files:
        img_path = os.path.join(input_folder, filename)
        print(f"- กำลังอ่าน {filename} ... (กำลังรอโมเดลตอบ อาจใช้เวลาสักครู่)", flush=True)
        start = time.time()
        try:
            data = extract_receipt_data(img_path)
            elapsed = time.time() - start

            # เก็บผลดิบไว้ดูย้อนหลังเป็นไฟล์ .json ต่อรูป
            json_path = os.path.join(out_dir, f"{os.path.splitext(filename)[0]}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            append_receipt_to_excel(data, excel_path, source_file=filename)

            low_conf = data.get("low_confidence_fields") or []
            flag = f" (ไม่มั่นใจ: {', '.join(low_conf)})" if low_conf else ""
            print(f"  สำเร็จ ({elapsed:.1f} วิ){flag}", flush=True)
            ok += 1
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ล้มเหลว ({elapsed:.1f} วิ): {e}", flush=True)
            failed += 1

    print(f"\nเสร็จสิ้น: สำเร็จ {ok} ไฟล์, ล้มเหลว {failed} ไฟล์")
    print(f"ผลลัพธ์อยู่ที่: {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("วิธีใช้: python batch_process.py path/to/photo_folder")
        sys.exit(1)
    main(sys.argv[1])