import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# กำหนด DIR ของไฟล์ document_generator.py โดยตรง
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

def generate_document_image(doc_type: str, data: dict, template_filename: str, output_filename: str) -> str:
    template_path = BASE_DIR / "templates" / template_filename
    output_dir = BASE_DIR / "static" / "generated_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ✅ ชี้ไปที่ THSarabunNew.ttf ในโฟลเดอร์เดียวกันโดยตรง
    font_path = CURRENT_DIR / "THSarabunNew.ttf"
    
    # ดึงฟอนต์ (ถ้าโหลดไม่ได้ ให้โยกไปใช้ Thonburi ของ Mac เพื่อป้องกันสี่เหลี่ยม)
    try:
        font_main = ImageFont.truetype(str(font_path), 40)
        font_bold = ImageFont.truetype(str(font_path), 48)
    except Exception as e:
        print(f"⚠️ โหลดฟอนต์ Sarabun ไม่สำเร็จ: {e}")
        font_main = ImageFont.truetype("/System/Library/Fonts/Supplemental/Thonburi.ttc", 36)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Thonburi.ttc", 44)

    # --- วาดข้อมูล ---
    customer_name = data.get("customer") or "-"
    credit_term = data.get("credit_term")
    term_text = f" (เครดิตเทอม {credit_term} วัน)" if credit_term else ""

    draw.text((220, 520), f"{customer_name}{term_text}", fill="#111111", font=font_main)

    start_y = 1150  
    item_name = data.get("item") or "รายการสินค้า"
    amount = float(data.get("amount") or 0.0)

    draw.text((180, start_y), "1", fill="#111111", font=font_main)
    draw.text((450, start_y), str(item_name), fill="#111111", font=font_main)
    draw.text((1480, start_y), "1", fill="#111111", font=font_main)
    draw.text((1720, start_y), f"{amount:,.2f}", fill="#111111", font=font_main)
    draw.text((2050, start_y), f"{amount:,.2f}", fill="#111111", font=font_main)

    draw.text((2050, 2100), f"{amount:,.2f}", fill="#111111", font=font_main)
    draw.text((2050, 2410), f"{amount:,.2f}", fill="#111111", font=font_bold)

    img.save(output_path, "JPEG", quality=95)
    return str(output_path)