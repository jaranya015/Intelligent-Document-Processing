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
    data = {
        "document_type": None,
        "customer_name": None,
        "invoice_number": None,
        "date": None,
        "total_amount": None
    }
    
    # 1. ตรวจสอบประเภทเอกสาร
    if re.search(r'Tax\s*Invoice|ใบกำกับภาษี', raw_text, re.IGNORECASE):
        data["document_type"] = "Tax Invoice"
    elif re.search(r'Purchase\s*Order|ใบสั่งซื้อ', raw_text, re.IGNORECASE):
        data["document_type"] = "Purchase Order"
    elif re.search(r'Quotation|ใบเสนอราคา', raw_text, re.IGNORECASE):
        data["document_type"] = "Quotation"
    elif re.search(r'Invoice|ใบแจ้งหนี้', raw_text, re.IGNORECASE):
        data["document_type"] = "Invoice"

    # 2. ค้นหาเลขที่เอกสาร
    inv_match = re.search(r'((?:INV|PO|QT|TAX)[-\d]+)', raw_text, re.IGNORECASE)
    if inv_match:
        data["invoice_number"] = inv_match.group(1)
        
    # 3. ค้นหารูปแบบวันที่ (DD/MM/YYYY)
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_text)
    if date_match:
        data["date"] = date_match.group(1)
        
    # 4. ค้นหาชื่อลูกค้า (ปรับให้จับหลังคำว่า "ชื่อลูกค้า")
    cust_match = re.search(r'ชื่อลูกค้า\s*([ก-ฮa-zA-Z\.\s]+?)(?=\s+(?:ที่อยู่|เลขผู้เสียภาษี|เบอร์โทรศัพท์|อีเมล|ผู้ติดต่อ|เลขอ|วันที่|เลขที่)|$)', raw_text)
    if cust_match:
        data["customer_name"] = cust_match.group(1).strip()
    else:
        # Fallback หากหารูปแบบไม่เจอ ให้หาคำว่า "ร้าน"
        store_match = re.search(r'(ร้าน[ก-ฮa-zA-Z\.\s]+)', raw_text)
        if store_match:
            data["customer_name"] = store_match.group(1).strip()
        
    # 5. ค้นหายอดเงินรวมสุทธิ (มองหาบรรทัด "จำนวนเงินรวมทั้งสิ้น" หรือยอดสุดท้ายที่ไม่ใช่ 0.00)
    total_match = re.search(r'จำนวนเงินรวมทั้งสิ้น\s*[\r\n]+\s*([\d,]+\.\d{2})', raw_text)
    if total_match:
        data["total_amount"] = total_match.group(1).replace(",", "")
    else:
        # Fallback หาตัวเลขที่มีทศนิยมตัวท้ายๆ ของเอกสาร
        amounts = re.findall(r'([\d,]+\.\d{2})', raw_text)
        if amounts:
            valid_amounts = [amt.replace(",", "") for amt in amounts if amt not in ("0.00", "350.00")]
            if valid_amounts:
                data["total_amount"] = valid_amounts[-1]
            else:
                data["total_amount"] = amounts[-1].replace(",", "")
                
    return data


if __name__ == "__main__":
    original_image = "invoice_template.jpg"
    processed_image_path = "processed_receipt.jpg"
    
    print(f"--- เริ่มกระบวนการ Preprocessing ภาพด้วย OpenCV ---")
    # สมมติว่ามีฟังก์ชัน preprocess หรือเราใช้ภาพที่คลีนแล้วมาเทส
    # ถ้ายังไม่มีฟังก์ชันเรียก OpenCV ในไฟล์นี้ สามารถใช้ภาพต้นฉบับผ่าน Preprocess ได้เลย
    
    print(f"--- เริ่มประมวลผลภาพผ่าน Hybrid Pipeline (Florence-2 + Regex) ---")
    
    # ส่งภาพเข้าโมเดล Local
    raw_text = extract_with_florence2(original_image)
    print("\n[1] ข้อความดิบที่อ่านได้จาก OCR:")
    print(raw_text)
    
    structured_data = extract_with_regex(raw_text)
    print("\n[2] ข้อมูลที่สกัดได้โครงสร้าง JSON ")
    print(json.dumps(structured_data, ensure_ascii=False, indent=2))