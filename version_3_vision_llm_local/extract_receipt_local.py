"""
extract_receipt_local.py

เวอร์ชันฟรี — ใช้โมเดล vision ที่รันบนเครื่องตัวเองผ่าน Ollama แทน Claude API
ไม่มีค่าใช้จ่ายเลย แต่ความแม่นยำ (โดยเฉพาะภาษาไทย/ตัวเลข) จะสู้ Claude ไม่ได้

ก่อนใช้ต้องดึงโมเดลก่อน:
    ollama pull qwen2.5vl

หมายเหตุ: ห้ามใช้ llama3.2-vision ตอนนี้ — Ollama engine เวอร์ชันใหม่ (0.30.0+)
ยังไม่รองรับสถาปัตยกรรม 'mllama' ของโมเดลนี้ รันแล้วจะเจอ error
"unknown model architecture: 'mllama'" เป็นบั๊กฝั่ง Ollama เอง ยังไม่มีกำหนดแก้
ใช้ qwen2.5vl หรือ llava แทนไปก่อน

วิธีใช้ (โครงสร้างและ interface เหมือน extract_receipt.py ทุกอย่าง
สลับไฟล์ import เดียวก็พอ ส่วน batch_process.py / excel_writer.py ใช้ร่วมกันได้เลย):
    python extract_receipt_local.py path/to/receipt.jpg

ต้องติดตั้งก่อน:
    pip install ollama pillow
"""

import io
import json
import os
import sys
import cv2
import numpy as np
import pytesseract
import re
import ollama
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
MODEL = "minicpm-v"
#MODEL = "llava-phi3"  #เพื่อให้ฟังก์ชันอ่านใบเสร็จรู้ว่าจะต้องใช้โมเดลตัวไหน
model="llama3.1"  # moondream เล็ก (~1.8GB) เหมาะกับเครื่อง RAM 8GB - เร็วกว่า qwen2.5vl/llama3.2-vision มาก
# หมายเหตุ: moondream แม่นยำน้อยกว่าโมเดลใหญ่ โดยเฉพาะภาษาไทยและตัวเลขละเอียด
# ถ้าเครื่องมี RAM มากกว่านี้ (16GB+) ค่อยลองสลับกลับไปเป็น "qwen2.5vl" เพื่อความแม่นยำที่ดีกว่า

MAX_DIMENSION = 1024

# ใช้ prompt เดียวกับเวอร์ชัน Claude เพื่อเทียบผลกันตรง ๆ ได้
EXTRACTION_PROMPT = """คุณคือผู้เชี่ยวชาญด้านบัญชีไทย หน้าที่ของคุณคือดูรูปใบเสร็จ/ใบกำกับภาษี/ใบเสนอราคานี้
แล้วสกัดข้อมูลออกมาเป็น JSON ที่ถูกต้องแม่นยำที่สุด โดยดูจากภาพโดยตรง (ไม่ใช่ข้อความ OCR)=

กฎการประมวลผล:
1. อ่านตัวเลขให้ระวังเป็นพิเศษ (จำนวนเงิน, เลขที่เอกสาร, เบอร์โทร, เลขภาษี) เพราะสำคัญที่สุด
2. ถ้าปีเป็น พ.ศ. (25xx) ให้แปลงเป็น ค.ศ. โดยลบ 543 แล้วค่อยใส่ในผลลัพธ์ (date ต้องเป็น ค.ศ. เสมอ)
3. ถ้าตัวเลขหรือข้อความใดในภาพเบลอ/อ่านไม่ชัดจนไม่มั่นใจ ให้ใส่ค่าที่อ่านได้ดีที่สุดแต่เพิ่มชื่อฟิลด์นั้น
   ลงใน "low_confidence_fields" ด้วย (list ของ string เช่น ["total", "items[0].price"])
4. ถ้าข้อมูลบางฟิลด์ไม่มีในเอกสารเลย ให้ใส่ null ห้ามเดามั่ว

โครงสร้าง JSON ที่ต้องการ (ตอบเป็น JSON ล้วน ๆ ไม่ต้องมีคำอธิบายอื่นหรือ markdown fence):
{
  "company": "ชื่อร้าน/บริษัทผู้ออกเอกสาร",
  "document_type": "Receipt | Invoice | Quotation | Tax Invoice | อื่นๆ",
  "document_no": "เลขที่เอกสาร ถ้ามี",
  "date": "YYYY-MM-DD",
  "tax_id": "เลขผู้เสียภาษี ถ้ามี",
  "items": [
    {"name": "ชื่อสินค้า/บริการ", "qty": 0, "unit_price": 0.0, "amount": 0.0}
  ],
  "subtotal": 0.0,
  "discount": 0.0,
  "vat": 0.0,
  "total": 0.0,
  "currency": "THB",
  "low_confidence_fields": []
}
"""

def extract_text_to_json(user_text: str) -> dict:
    prompt = f"""คุณคือระบบช่วยออกเอกสารบัญชีภาษาไทย
โปรดอ่านข้อความต่อไปนี้แล้วสกัดข้อมูลออกมาเป็น JSON (ตอบเฉพาะ JSON เท่านั้น ห้ามใส่คำอธิบายเพิ่มเติม):
"{user_text}"

โครงสร้าง JSON ที่ต้องการ (ให้สกัดข้อมูลจากข้อความเท่านั้น ถ้าข้อมูลไหนไม่มีให้ใส่ null):
{{
  "customer_name": "ชื่อลูกค้า หรือ ชื่อร้านค้า",
  "customer_address": "ที่อยู่ลูกค้า",
  "customer_tax_id": "เลขผู้เสียภาษีลูกค้า",
  "customer_phone": "เบอร์โทรศัพท์ลูกค้า",
  "customer_email": "อีเมลลูกค้า",
  "customer_contact": "ชื่อผู้ติดต่อ",
  "item_name": "ชื่อสินค้าหรือบริการที่ลูกค้าสั่ง",
  "qty": 0,
  "unit_price": 0.0,
  "amount": 0.0,
  "credit_term": "จำนวนวันเครดิต"
}}
"""
    response = ollama.chat(
        model="llama3.1",
        messages=[{"role": "user", "content": prompt}],
        format="json"
    )
    return json.loads(response["message"]["content"].strip())

def _resize_to_temp(image_path: str) -> str:
    """ย่อรูปถ้าใหญ่เกิน แล้วเซฟเป็นไฟล์ชั่วคราว (ollama.chat รับ path ของไฟล์บนดิสก์)"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > MAX_DIMENSION:
        scale = MAX_DIMENSION / longest
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    tmp_path = image_path + ".resized.jpg"
    img.save(tmp_path, format="JPEG", quality=92)
    return tmp_path


def extract_receipt_data(image_path: str) -> dict:
    """เหมือน extract_receipt.py ทุกอย่าง แต่เรียกโมเดล local ผ่าน Ollama แทน"""
    resized_path = _resize_to_temp(image_path)

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [resized_path],
                }
            ],
            format="json",
            options={
                "num_ctx": 4096 
            },
        )
        raw_text = response["message"]["content"].strip()
    finally:
        # เก็บกวาดไฟล์ชั่วคราว
        if os.path.exists(resized_path):
            os.remove(resized_path)

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"โมเดล local ตอบมาไม่ใช่ JSON ที่ parse ได้: {e}\n--- raw response ---\n{raw_text}"
        ) from e

    return data

def preprocess_image(image_path):
    # 1. โหลดภาพแบบ Grayscale (ภาพขาวดำ)
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # 2. ปรับความคมชัดและลดสัญญาณรบกวน (Denoising)
    denoised = cv2.fastNlMeansDenoising(img, h=30)
    
    # 3. ทำ Thresholding (Adaptive Threshold) เพื่อให้ตัวหนังสือตัดกับพื้นหลังชัดเจน
    # ช่วยแก้ปัญหาใบเสร็จที่แสงเงาไม่สม่ำเสมอ
    thresh = cv2.adaptiveThreshold(
        denoised, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # (ทางเลือก) บันทึกภาพที่ปรับปรุงแล้วเพื่อตรวจสอบ
    processed_path = "processed_receipt.jpg"
    cv2.imwrite(processed_path, thresh)
    
    return processed_path

def extract_text_local(image_path):
    # 1. ทำ Image Preprocessing ก่อน
    processed_image_path = preprocess_image(image_path)
    
    # 2. นำภาพที่ผ่านการคลีนแล้วไปทำ OCR (ตัวอย่างการใช้ Tesseract รองรับไทย+อังกฤษ)
    processed_img = cv2.imread(processed_image_path)
    custom_config = r'--oem 3 --psm 6 -l tha+eng'
    raw_text = pytesseract.image_to_string(processed_img, config=custom_config)
    
    return raw_text

def extract_with_regex(raw_text):
    # ค้นหารูปแบบวันที่ เช่น DD/MM/YYYY หรือ DD-MM-YYYY
    date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
    dates = re.findall(date_pattern, raw_text)
    
    # ค้นหารูปแบบจำนวนเงิน (เช่น ยอดรวม, Total, ฿)
    price_pattern = r'(?:รวมทั้งสิ้น|รวมเงิน|Total|NET)?\s*[:]?\s*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})'
    prices = re.findall(price_pattern, raw_text)
    
    return {
        "extracted_dates": dates,
        "extracted_prices": prices
    }


    
if __name__ == "__main__":
    test_image_path = "invoice_template.jpg"  
    
    if os.path.exists(test_image_path):
        print("--- เริ่มทดสอบ Vision Model ผ่าน Ollama ---")
        # เปลี่ยนมาเรียกฟังก์ชันดึงข้อมูลด้วย Vision LLM แทน Tesseract OCR
        result = extract_receipt_data(test_image_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ไม่พบไฟล์รูปภาพสำหรับทดสอบ: {test_image_path}")
'''
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("วิธีใช้ python extract_receipt_local.py path/to/receipt.jpg")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"ไม่พบไฟล์: {path}")
        sys.exit(1)

    result = extract_receipt_data(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))

'''

    