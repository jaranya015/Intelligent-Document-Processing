import json
import base64
import requests
from PIL import Image

# URL ของ Ollama ที่รันอยู่ในเครื่อง
OLLAMA_URL = "http://localhost:11434/api/generate"
#MODEL_NAME = "llama3.2-vision"
MODEL_NAME = "llava-phi3"

EXTRACTION_PROMPT = """คุณคือผู้เชี่ยวชาญด้านบัญชีไทย หน้าที่ของคุณคือดูรูปใบเสร็จ/ใบกำกับภาษี/ใบเสนอราคานี้
แล้วสกัดข้อมูลออกมาเป็น JSON ที่ถูกต้องแม่นยำที่สุด โดยดูจากภาพโดยตรง

โครงสร้าง JSON ที่ต้องการ (ถ้าฟิลด์ไหนไม่มีให้ใส่ null):
{
  "company": "ชื่อร้าน/บริษัทผู้ออกเอกสาร",
  "document_type": "Receipt | Invoice | Quotation | Tax Invoice | อื่นๆ",
  "document_no": "เลขที่เอกสาร",
  "date": "YYYY-MM-DD",
  "tax_id": "เลขผู้เสียภาษี",
  "items": [
    {"name": "ชื่อสินค้า/บริการ", "qty": 0, "unit_price": 0.0, "amount": 0.0}
  ],
  "subtotal": 0.0,
  "discount": 0.0,
  "vat": 0.0,
  "total": 0.0,
  "currency": "THB",
  "low_confidence_fields": []
}"""

def extract_text_to_json(user_text: str) -> dict:
    prompt = f"""คุณคือระบบช่วยออกเอกสารบัญชีภาษาไทย โปรดอ่านข้อความต่อไปนี้แล้วสกัดข้อมูลออกมาเป็น JSON:
"{user_text}"

โครงสร้าง JSON ที่ต้องการ:
{{
  "customer_name": "ชื่อลูกค้า หรือ ชื่อร้านค้า (ถ้าไม่มีใส่ null)",
  "customer_address": "ที่อยู่ลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_tax_id": "เลขผู้เสียภาษีลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_phone": "เบอร์โทรศัพท์ลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_email": "อีเมลลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_contact": "ชื่อผู้ติดต่อ (ถ้าไม่มีใส่ null)",
  "item_name": "ชื่อสินค้า/บริการ (เช่น หมู)",
  "qty": 1,
  "unit_price": 500.0,
  "amount": 500.0,
  "credit_term": "15"
}}"""
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    
    response = requests.post(OLLAMA_URL, json=payload)
    response_data = response.json()
    
    # เช็กว่า Ollama ส่งผลลัพธ์มาปกติ หรือส่ง Error มา
    if 'response' not in response_data:
        print("Ollama API Error (Text):", response_data)
        raise ValueError(f"Ollama Error: {response_data.get('error', 'Unknown Error')}")
        
    return json.loads(response_data['response'])

def extract_receipt_data(image_path: str) -> dict:
    # แปลงรูปภาพเป็น Base64 เพื่อส่งให้ Ollama
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    payload = {
        "model": MODEL_NAME,
        "prompt": EXTRACTION_PROMPT,
        "images": [encoded_string],
        "format": "json",
        "stream": False
    }
    
    response = requests.post(OLLAMA_URL, json=payload)
    response_data = response.json()
    
    # เช็กว่า Ollama ส่งผลลัพธ์มาปกติ หรือส่ง Error มา
    if 'response' not in response_data:
        print("Ollama API Error (Image):", response_data)
        raise ValueError(f"Ollama Error: {response_data.get('error', 'Unknown Error')}")
        
    return json.loads(response_data['response'])













'''import json
from PIL import Image
from version_3_vision_llm_local import config

# ใช้ Library ตัวใหม่ google-genai
from google import genai
from google.genai import types

# ตั้งค่า Client
client = genai.Client(api_key=config.GOOGLE_API_KEY)

# ใช้โมเดล Gemini 1.5 Flash
#MODEL_NAME = "gemini-1.5-flash"
#MODEL_NAME = "gemini-2.0-flash"
MODEL_NAME = "gemini-3.8-flash"

EXTRACTION_PROMPT = """คุณคือผู้เชี่ยวชาญด้านบัญชีไทย หน้าที่ของคุณคือดูรูปใบเสร็จ/ใบกำกับภาษี/ใบเสนอราคานี้
แล้วสกัดข้อมูลออกมาเป็น JSON ที่ถูกต้องแม่นยำที่สุด โดยดูจากภาพโดยตรง

กฎการประมวลผล:
1. อ่านตัวเลขให้ระวังเป็นพิเศษ (จำนวนเงิน, เลขที่เอกสาร, เบอร์โทร, เลขภาษี) เพราะสำคัญที่สุด
2. ถ้าปีเป็น พ.ศ. (25xx) ให้แปลงเป็น ค.ศ. โดยลบ 543 แล้วค่อยใส่ในผลลัพธ์ (date ต้องเป็น ค.ศ. เสมอ)
3. ถ้าตัวเลขหรือข้อความใดในภาพเบลอ/อ่านไม่ชัดจนไม่มั่นใจ ให้ใส่ค่าที่อ่านได้ดีที่สุดแต่เพิ่มชื่อฟิลด์นั้น
   ลงใน "low_confidence_fields" ด้วย (list ของ string เช่น ["total", "items[0].price"])
4. ถ้าข้อมูลบางฟิลด์ไม่มีในเอกสารเลย ให้ใส่ null ห้ามเดามั่ว

โครงสร้าง JSON ที่ต้องการ:
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
}"""

def extract_text_to_json(user_text: str) -> dict:
    prompt = f"""คุณคือระบบช่วยออกเอกสารบัญชีภาษาไทย
โปรดอ่านข้อความต่อไปนี้แล้วสกัดข้อมูลออกมาเป็น JSON:
"{user_text}"

โครงสร้าง JSON ที่ต้องการ:
{{
  "customer_name": "ชื่อลูกค้า หรือ ชื่อร้านค้า (ถ้าไม่มีใส่ null)",
  "customer_address": "ที่อยู่ลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_tax_id": "เลขผู้เสียภาษีลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_phone": "เบอร์โทรศัพท์ลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_email": "อีเมลลูกค้า (ถ้าไม่มีใส่ null)",
  "customer_contact": "ชื่อผู้ติดต่อ (ถ้าไม่มีใส่ null)",
  "item_name": "ชื่อสินค้า/บริการ (เช่น หมู)",
  "qty": 1,
  "unit_price": 500.0,
  "amount": 500.0,
  "credit_term": "15"
}}"""
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

def extract_receipt_data(image_path: str) -> dict:
    img = Image.open(image_path)
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[EXTRACTION_PROMPT, img],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

'''