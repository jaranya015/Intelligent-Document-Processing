import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

def preprocess_receipt(image_path):
    """ฟังก์ชันประมวลผลใบเสร็จ: ตัดขอบ, ทำ Grayscale และกรองเฉพาะอักษรดำ"""
    # 1. โหลดภาพต้นฉบับ
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # 2. การตัดขอบภาพอัตโนมัติ (Automatic Cropping)
    gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred_full = cv2.GaussianBlur(gray_full, (7, 7), 0)
    _, thresh_crop = cv2.threshold(blurred_full, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh_crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        if w > 0.1 * img.shape[1] and h > 0.1 * img.shape[0]:
            cropped_img = img[y:y+h, x:x+w]
        else:
            cropped_img = img
    else:
        cropped_img = img

    # 3. การกรองตัวอักษรดำ (Black Text Filtering)
    gray_cropped = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
    blurred_final = cv2.GaussianBlur(gray_cropped, (5, 5), 0)
    thresh_final = cv2.adaptiveThreshold(
        blurred_final, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 4
    )
    
    # 4. การลบจุดรบกวน (Denoising & Morphology)
    kernel = np.ones((2, 2), np.uint8)
    thresh_final = cv2.morphologyEx(thresh_final, cv2.MORPH_OPEN, kernel)

    # --- ค่า Threshold สำหรับกรองตัวอักษร ---
    min_w, min_h = 2, 3       
    max_w, max_h = 50, 80   
    min_aspect_ratio = 0.1    
    max_aspect_ratio = 5.0    

    contours_final, _ = cv2.findContours(thresh_final, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    final_img_clean = np.ones_like(thresh_final) * 255
    
    for cnt in contours_final:
        x_t, y_t, w_t, h_t = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        aspect_ratio = float(w_t) / h_t
        
        if (min_w < w_t < max_w and min_h < h_t < max_h and 
            min_aspect_ratio < aspect_ratio < max_aspect_ratio and
            area > 15): 
            cv2.drawContours(final_img_clean, [cnt], -1, (0), -1) 
    
    return final_img_clean

# --- ส่วนของการตั้งค่า Path ---
input_folder = '/Users/faiijaran/Desktop/project/photo_for_test/'
output_folder = '/Users/faiijaran/Desktop/project/output/photo_by_grayscale/'
num_images = 16

# สร้างโฟลเดอร์ output ถ้ายังไม่มี
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"📁 สร้างโฟลเดอร์ใหม่ที่: {output_folder}")

print(f"🚀 เริ่มประมวลผลทั้งหมด {num_images} ไฟล์...")

for i in range(1, num_images + 1):
    filename = f"{i}.jpeg"
    full_path = os.path.join(input_folder, filename)
    
    processed_image = preprocess_receipt(full_path)
    
    if processed_image is not None:
        # บันทึกรูปภาพลงในโฟลเดอร์ output
        output_filename = f"grayscale_{i}.png"
        output_path = os.path.join(output_folder, output_filename)
        cv2.imwrite(output_path, processed_image)
        
        print(f"✅ บันทึกสำเร็จ: {output_filename}")
        
        # แสดงผลในหน้าจอ (ถ้าเปิดผ่าน Jupyter)
        plt.figure(figsize=(5, 5))
        plt.imshow(processed_image, cmap='gray')
        plt.title(f"Saved: {output_filename}")
        plt.axis("off")
        plt.show()
    else:
        print(f"❌ ไม่พบไฟล์หรือประมวลผลไม่ได้: {filename}")

print(f"\n✨ เสร็จเรียบร้อย! รูปทั้งหมดอยู่ที่: {output_folder}")