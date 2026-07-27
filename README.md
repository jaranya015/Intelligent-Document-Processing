# 🧾 Accounting Assistant & Document Generator LINE Bot (Local LLM Version)

ระบบผู้ช่วยจัดการเอกสารบัญชีและออกเอกสารการค้าอัตโนมัติผ่าน LINE Official Account โดยประมวลผลผ่าน **Local Vision-LLM (Ollama)** ในเครื่องเพื่อความเป็นส่วนตัวของข้อมูล และไม่มีค่าใช้จ่าย API สกัดข้อมูลใบเสร็จลง Excel พร้อมระบบออกใบเสนอราคา/ใบแจ้งหนี้/ใบสั่งซื้ออัตโนมัติ

---

## 🌟 ฟีเจอร์หลัก (Features)

1. **สกัดข้อมูลใบเสร็จอัตโนมัติ (Receipt OCR & Extraction):**
   - ส่งรูปใบเสร็จ/บิลซื้อเข้ามาใน LINE
   - ใช้ Local Vision LLM (`llava-phi3` / `qwen2.5vl`) สกัดข้อมูล เช่น ชื่อร้าน, วันที่, เลขผู้เสียภาษี, ยอดรวม
   - แสดงผล Flex Message ให้ผู้ใช้ตรวจสอบก่อนบันทึกลงไฟล์ Excel (`receipts.xlsx`)

2. **ออกเอกสารการค้าดิจิทัล (Automated Document Generator):**
   - สลับโหมดผ่าน Flex Menu (`ออกใบแจ้งหนี้`, `ใบเสนอราคา`, `ใบสั่งซื้อ`, `ใบกำกับภาษี`)
   - พิมพ์ข้อความคำสั่งซื้อภาษาไทยแบบเป็นกันเอง (เช่น *"ลูกค้า ร้านหมูปิ้ง สั่งหมู 5 kg 500 บาท เครดิต 15 วัน"*)
   - ระบบใช้ LLM สกัดข้อความภาษาไทยเป็น JSON แล้วนำไปวาดลงบน Template รูปภาพเอกสาร (`Pillow`)
   - ส่งรูปภาพเอกสารฉบับสมบูรณ์กลับให้ผู้ใช้ทาง LINE ทันที

3. **ทำงานแบบ Asynchronous & Local First:**
   - ใช้ **FastAPI Background Tasks** ตอบกลับ LINE ภายใน 0.1 วินาที ป้องกัน Webhook Timeout
   - ประมวลผลโมเดลภาษาผ่าน **Ollama Engine** บนเครื่องตัวเอง ไม่ต้องพึ่งพา Cloud API ชำระเงิน

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```text
PROJECT/
├── static/
│   └── generated_docs/          # โฟลเดอร์เก็บรูปภาพเอกสารที่ถูกสร้างขึ้น
├── temp_images/                 # โฟลเดอร์เก็บรูปภาพชั่วคราวที่ดาวน์โหลดจาก LINE
├── templates/                   # รูปภาพแม่แบบเอกสาร (Invoice, Quotation, PO, Tax Invoice)
│   ├── invoice_template.jpg
│   ├── quotation_template.jpg
│   ├── po_template.jpg
│   └── tax_invoice_template.jpg
├── version_3_vision_llm_local/
│   ├── batch_process.py         # สคริปต์รันสกัดข้อมูลรูปใบเสร็จยกโฟลเดอร์
│   ├── config.py                # โหลดค่าคอนฟิกและ Environment Variables
│   ├── document_generator.py    # ฟังก์ชันวาดข้อความลงแม่แบบรูปภาพ (Pillow/ImageDraw)
│   ├── excel_writer.py          # ฟังก์ชันบันทึกข้อมูลเข้าไฟล์ Excel (.xlsx)
│   ├── extract_receipt_local.py # ตัวเชื่อมต่อ Ollama API สกัดข้อความและรูปภาพเป็น JSON
│   ├── line_flex.py             # ฟังก์ชันสร้าง Flex Message UI สำหรับ LINE
│   ├── main.py                  # FastAPI Webhook Server จัดการ Event จาก LINE
│   └── THSarabunNew.ttf         # ฟอนต์ภาษาไทยสำหรับสร้างเอกสาร
├── .env                         # ไฟล์เก็บ Secret Key และ Tokens
├── .gitignore
├── README.md
└── requirements.txt
