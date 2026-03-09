import os
import easyocr
import cv2

# 1. กำหนดเส้นทาง Path
input_folder = '/Users/faiijaran/Desktop/project/version_2/output/photo_by_grayscale'
output_txt_folder = '/Users/faiijaran/Desktop/project/version_2/output/extracted_text'

# สร้างโฟลเดอร์สำหรับเก็บไฟล์ Text หากยังไม่มี
if not os.path.exists(output_txt_folder):
    os.makedirs(output_txt_folder)
    print(f"📁 สร้างโฟลเดอร์เก็บข้อมูล: {output_txt_folder}")

# 2. โหลดโมเดล EasyOCR
print("⌛ กำลังโหลดโมเดล EasyOCR...")
reader = easyocr.Reader(['th', 'en'])

def get_perfect_lines(image_path):
    # อ่านข้อความแบบละเอียด (paragraph=False) เพื่อช่วยเรื่องแยกคอลัมน์
    results = reader.readtext(image_path, paragraph=False)
    
    if not results:
        return ""

    # เรียงลำดับพิกัด Y (บนลงล่าง)
    results.sort(key=lambda x: x[0][0][1])
    
    lines = []
    if results:
        current_line_blocks = [results[0]]
        y_threshold = 8 # สำหรับไฟล์ดิจิทัลแนะนำที่ 8 พิกเซล

        for i in range(1, len(results)):
            prev_y = current_line_blocks[-1][0][0][1]
            curr_y = results[i][0][0][1]
            
            if abs(curr_y - prev_y) <= y_threshold:
                current_line_blocks.append(results[i])
            else:
                # เรียงลำดับ X (ซ้ายไปขวา) ภายในบรรทัด
                current_line_blocks.sort(key=lambda x: x[0][0][0])
                line_text = " ".join([b[1] for b in current_line_blocks])
                lines.append(line_text)
                current_line_blocks = [results[i]]
        
        # เก็บตกบรรทัดสุดท้าย
        current_line_blocks.sort(key=lambda x: x[0][0][0])
        lines.append(" ".join([b[1] for b in current_line_blocks]))

    return "\n".join(lines)

# 3. เริ่มประมวลผลและบันทึกไฟล์
print(f"🚀 เริ่มประมวลผลรูปภาพจาก: {input_folder}")
print("=" * 60)

# ดึงไฟล์ gray_1.png ถึง gray_10.png
target_files = [f for f in os.listdir(input_folder) if f.startswith('gray_') and f.endswith('.png')]
target_files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))

for filename in target_files:
    img_path = os.path.join(input_folder, filename)
    
    try:
        final_text = get_perfect_lines(img_path)
        
        # --- ส่วนการบันทึกไฟล์ ---
        # ตั้งชื่อไฟล์ใหม่จาก gray_1.png เป็น text_1.txt
        txt_filename = filename.replace('gray_', 'text_').replace('.png', '.txt')
        txt_path = os.path.join(output_txt_folder, txt_filename)
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(final_text)
        
        # แสดงผลในคอนโซลเพื่อให้คุณเห็นสถานะ
        print(f"✅ สำเร็จ: {filename} -> {txt_filename}")
        
    except Exception as e:
        print(f"❌ Error ในไฟล์ {filename}: {e}")

print(f"\n✨ เสร็จสมบูรณ์! ข้อมูลตัวอักษรทั้งหมดถูกเก็บไว้ที่: {output_txt_folder}")