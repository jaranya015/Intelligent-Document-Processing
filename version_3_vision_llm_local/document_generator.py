import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

# 🏢 ข้อมูลผู้ออกเอกสาร 
MY_COMPANY = {
    "name": "บริษัท pixxie woman จำกัด",
    "address": "หาดใหญ่ สงขลา 90110",
    "tax_id": "1234567890123",
    "phone": "084-2329-514",
    "email": "faiijaran0159@gmail.com",
    "bank_name": "กสิกรไทย (KBANK)",
    "bank_account": "1234-5-67890-1"
}

def generate_document_image(doc_type: str, data: dict, template_filename: str, output_filename: str) -> str:
    template_path = BASE_DIR / "templates" / template_filename
    output_dir = BASE_DIR / "static" / "generated_docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_path = CURRENT_DIR / "THSarabunNew.ttf"
    try:
        font_main = ImageFont.truetype(str(font_path), 36)
        font_bold = ImageFont.truetype(str(font_path), 40)
        font_small = ImageFont.truetype(str(font_path), 30)
    except Exception:
        font_main = ImageFont.truetype("/System/Library/Fonts/Supplemental/Thonburi.ttc", 30)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Thonburi.ttc", 34)
        font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Thonburi.ttc", 26)

    color_black = "#111111"

    # ==================== 1. ฝั่งลูกค้า (ซ้ายบน) ====================
    draw.text((150, 165), str(data.get("customer_name") or "-"), fill=color_black, font=font_main)
    draw.text((150, 195), str(data.get("customer_address") or "-"), fill=color_black, font=font_small)
    draw.text((150, 225), str(data.get("customer_tax_id") or "-"), fill=color_black, font=font_small)
    draw.text((150, 255), str(data.get("customer_contact") or "-"), fill=color_black, font=font_small)
    
    draw.text((360, 225), str(data.get("customer_email") or "-"), fill=color_black, font=font_small)
    draw.text((360, 255), str(data.get("customer_phone") or "-"), fill=color_black, font=font_small)

    # ==================== 2. ข้อมูลเอกสาร (ขวาบน) ====================
    today_str = datetime.now().strftime("%d/%m/%Y")
    credit_days = int(data.get("credit_term") or 0)
    due_date_str = (datetime.now() + timedelta(days=credit_days)).strftime("%d/%m/%Y") if credit_days > 0 else "-"

    draw.text((720, 165), f"INV-{datetime.now().strftime('%Y%m%d%H%M')}", fill=color_black, font=font_main) # เลขที่
    draw.text((720, 195), today_str, fill=color_black, font=font_main)                                   # วันที่
    draw.text((720, 225), due_date_str, fill=color_black, font=font_main)                                # ครบกำหนด
    draw.text((720, 255), f"{credit_days} วัน" if credit_days > 0 else "-", fill=color_black, font=font_main) # อ้างอิง

    # ==================== 3. ฝั่งผู้ออกเอกสาร/ร้านเรา (กลางบน) ====================
    draw.text((151, 320+206), MY_COMPANY["name"], fill=color_black, font=font_small)
    draw.text((150, 345+213), MY_COMPANY["address"], fill=color_black, font=font_small)
    draw.text((880+50, 320+206), MY_COMPANY["tax_id"], fill=color_black, font=font_small)
    draw.text((880+50, 345+213), MY_COMPANY["phone"], fill=color_black, font=font_small)
    draw.text((880+50, 370+220), MY_COMPANY["email"], fill=color_black, font=font_small)

    # ==================== 4. ตารางรายการสินค้า ====================
    item_name = data.get("item_name") or data.get("item") or "รายการสินค้า"
    qty = data.get("qty") or 1
    
    try:
        amount = float(data.get("amount") or 0.0)
        unit_price = float(data.get("unit_price") or amount)
    except (ValueError, TypeError):
        amount = 0.0
        unit_price = 0.0

    start_y = 740  # บรรทัดแรกในตารางสินค้า
    draw.text((80, start_y), "1", fill=color_black, font=font_main)
    draw.text((200+200, start_y), str(item_name), fill=color_black, font=font_main)
    draw.text((600+200+90, start_y), str(qty), fill=color_black, font=font_main)
    draw.text((700+200+100, start_y), f"{unit_price:,.2f}", fill=color_black, font=font_main)
    draw.text((840+200+130, start_y), f"{amount:,.2f}", fill=color_black, font=font_main)

    # ==================== 5. สรุปยอดเงิน (ขวาล่าง) ====================
    draw.text((880+150, 770+400), f"{amount:,.2f}", fill=color_black, font=font_main)         # ราคารวม
    draw.text((880+150, 890+480), f"{amount:,.2f}", fill=color_black, font=font_bold)         # รวมทั้งสิ้น

    # ==================== 6. ช่องทางการชำระเงิน (ซ้ายล่าง) ====================
    draw.text((150+45, 970+580), MY_COMPANY["bank_name"], fill=color_black, font=font_small)
    draw.text((150+45, 1000+595), MY_COMPANY["bank_account"], fill=color_black, font=font_small)

    img.save(output_path, "JPEG", quality=95)
    return str(output_path)