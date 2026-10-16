import os
import re
import json
import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

MODEL_ID = 'microsoft/Florence-2-large'

print("--- กำลังโหลดโมเดล Florence-2 เข้าสู่เครื่อง (Local) ---")
device = "cuda" if torch.cuda.is_available() else "cpu"

processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, 
    trust_remote_code=True, 
    attn_implementation="eager"
).to(device)

def extract_with_florence2(image_path):
    if not os.path.exists(image_path):
        return {"error": f"ไม่พบไฟล์รูปภาพ: {image_path}"}
    
    image = Image.open(image_path).convert("RGB")
    task_prompt = "<OCR>"
    
    inputs = processor(text=task_prompt, images=image, return_tensors="pt").to(device)
    
    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            do_sample=False,
            num_beams=1,
            use_cache=False
        )
    
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = processor.post_process_generation(generated_text, task=task_prompt, image_size=image.size)
    
    return parsed_answer.get("<OCR>", "")

def extract_with_regex(raw_text):
    """สกัดข้อมูลแบบ Dynamic รองรับเอกสารหลายประเภท (Invoice, PO, Quotation, Tax Invoice)"""
    data = {
        "document_type": None,
        "customer_name": None,
        "invoice_number": None,
        "date": None,
        "total_amount": None
    }
    
    # 1. ตรวจสอบประเภทเอกสารจากหัวกระดาษ
    if re.search(r'Tax\s*Invoice|ใบกำกับภาษี', raw_text, re.IGNORECASE):
        data["document_type"] = "Tax Invoice"
    elif re.search(r'Purchase\s*Order|ใบสั่งซื้อ', raw_text, re.IGNORECASE):
        data["document_type"] = "Purchase Order"
    elif re.search(r'Quotation|ใบเสนอราคา', raw_text, re.IGNORECASE):
        data["document_type"] = "Quotation"
    elif re.search(r'Invoice|ใบแจ้งหนี้', raw_text, re.IGNORECASE):
        data["document_type"] = "Invoice"

    # 2. ค้นหาเลขที่เอกสาร (รองรับทั้ง INV-, PO-, QT- หรือรหัสตัวเลขใกล้เคียง)
    inv_match = re.search(r'((?:INV|PO|QT|TAX)[-\d]+)', raw_text, re.IGNORECASE)
    if inv_match:
        data["invoice_number"] = inv_match.group(1)
    else:
        # Fallback กรณีรูปแบบรหัสต่างออกไป
        fallback_inv = re.search(r'(INV-[\d]+)', raw_text, re.IGNORECASE)
        if fallback_inv:
            data["invoice_number"] = fallback_inv.group(1)
        
    # 3. ค้นหารูปแบบวันที่ (DD/MM/YYYY)
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_text)
    if date_match:
        data["date"] = date_match.group(1)
        
    # 4. ค้นหาชื่อลูกค้า (ดึงข้อความหลังคำว่า ชื่อลูกค้า หรือ ร้าน)
    cust_match = re.search(r'(?:ชื่อลูกค้า|ร้าน)\s*[:\-]?\s*([ก-ฮa-zA-Z\.\s]+)', raw_text)
    if cust_match:
        data["customer_name"] = cust_match.group(1).strip()
        
    # 5. ค้นหายอดเงินรวมสุทธิ (มองหาตัวเลขที่มีทศนิยมกลุ่มท้ายๆ ของเอกสาร)
    amounts = re.findall(r'([\d,]+\.\d{2})', raw_text)
    if amounts:
        # เลือกตัวเลขที่เป็นเรทราคาสุทธิ (ตัดตัวเลขที่เป็น 0.00 หรือพวกจำนวนเงินย่อยออกถ้าเป็นไปได้)
        valid_amounts = [amt for amt in amounts if amt != "0.00"]
        if valid_amounts:
            data["total_amount"] = valid_amounts[-1]  # มักจะเป็นยอดรวมสุทธิตัวสุดท้าย
        else:
            data["total_amount"] = amounts[-1]
        
    return data


if __name__ == "__main__":
    test_image = "invoice_template.jpg"
    print(f"--- เริ่มประมวลผลภาพ {test_image} ด้วย Hybrid Pipeline (Florence-2 + Regex) ---")
    
    # 1. ดึงข้อความดิบด้วย Local OCR
    raw_text = extract_with_florence2(test_image)
    print("\n[1] ข้อความดิบที่อ่านได้จาก OCR:")
    print(raw_text)
    
    # 2. สกัดข้อมูลด้วย Regex
    structured_data = extract_with_regex(raw_text)
    print("\n[2] ข้อมูลที่สกัดได้โครงสร้าง JSON สวยๆ:")
    print(json.dumps(structured_data, ensure_ascii=False, indent=2))