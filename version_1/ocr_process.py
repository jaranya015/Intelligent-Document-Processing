import os
import easyocr
import cv2

# 1. ตั้งค่า Path
input_folder = '/Users/faiijaran/Desktop/project/output/photo_by_grayscale'
output_txt_folder = '/Users/faiijaran/Desktop/project/output/extracted_text'

# สร้างโฟลเดอร์สำหรับเก็บไฟล์ Text
if not os.path.exists(output_txt_folder):
    os.makedirs(output_txt_folder)

# 2. เตรียม EasyOCR (ไทย + อังกฤษ)
print("กำลังโหลดโมเดล OCR...")
reader = easyocr.Reader(['th', 'en'])

def get_sorted_text(image_path):
    # อ่านข้อความพร้อมพิกัด
    results = reader.readtext(image_path)
    
    # เรียงลำดับจาก บนลงล่าง (Y) และ ซ้ายไปขวา (X)
    results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))
    
    lines = []
    current_line = ""
    last_y = -1
    threshold = 15 # ระยะห่างที่ถือว่าเป็นบรรทัดเดียวกัน

    for (bbox, text, prob) in results:
        top_left_y = bbox[0][1]
        
        if last_y == -1 or abs(top_left_y - last_y) <= threshold:
            current_line += " " + text
        else:
            lines.append(current_line.strip())
            current_line = text
        last_y = top_left_y
        
    if current_line:
        lines.append(current_line.strip())
        
    return "\n".join(lines)

# 3. วนลูปอ่านรูป grayscale_1 ถึง grayscale_16
print(f"🚀 เริ่มดึงข้อความจาก {input_folder}...")

for i in range(1, 17):
    filename = f"grayscale_{i}.png"
    img_path = os.path.join(input_folder, filename)
    
    if os.path.exists(img_path):
        try:
            structured_text = get_sorted_text(img_path)
            
            # บันทึกเป็นไฟล์ .txt
            txt_filename = f"text_{i}.txt"
            txt_path = os.path.join(output_txt_folder, txt_filename)
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(structured_text)
            
            print(f"✅ OCR สำเร็จ: {txt_filename}")
        except Exception as e:
            print(f"❌ พลาดที่ไฟล์ {filename}: {e}")
    else:
        print(f"⚠️ ไม่พบไฟล์: {filename}")

print(f"\n✨ เสร็จสิ้น! ข้อความทั้งหมดอยู่ที่: {output_txt_folder}")