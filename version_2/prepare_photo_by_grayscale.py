import os
import cv2
import matplotlib.pyplot as plt

# 1. กำหนดเส้นทางโฟลเดอร์
input_folder = '/Users/faiijaran/Desktop/project/version_2/photo_for_test'
output_folder = '/Users/faiijaran/Desktop/project/version_2/output/photo_by_grayscale'
valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')

# สร้างโฟลเดอร์ output หากยังไม่มี
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"📁 สร้างโฟลเดอร์ใหม่ที่: {output_folder}")

# 2. ตั้งค่า DPI สำหรับการโชว์ผลใน Jupyter
plt.rcParams['figure.dpi'] = 150 

print(f"🚀 เริ่มประมวลผลและบันทึกรูปภาพ...")

files = [f for f in os.listdir(input_folder) if f.lower().endswith(valid_extensions)]
files.sort()

for filename in files:
    input_path = os.path.join(input_folder, filename)
    img = cv2.imread(input_path)
    
    if img is not None:
        # แปลงเป็น Grayscale (รักษาความคมชัดสูงสุด)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # --- ส่วนการบันทึกไฟล์ ---
        # ตั้งชื่อใหม่โดยเติม gray_ นำหน้า (เช่น 1.jpg -> gray_1.png)
        output_filename = f"gray_{os.path.splitext(filename)[0]}.png"
        output_path = os.path.join(output_folder, output_filename)
        cv2.imwrite(output_path, gray_img)
        
        # --- ส่วนแสดงผลใน Jupyter (Sharp View) ---
        plt.figure(figsize=(10, 10))
        plt.imshow(gray_img, cmap='gray', interpolation='none')
        plt.title(f"📄 Sharp View & Saved: {output_filename}")
        plt.axis("off")
        plt.show()
        
        print(f"✅ บันทึกสำเร็จ: {output_filename}")
        print("-" * 50)
    else:
        print(f"❌ ไม่สามารถอ่านไฟล์: {filename}")

print(f"\n✨ เสร็จเรียบร้อย! รูปทั้งหมดถูกเก็บไว้ที่: {output_folder}")