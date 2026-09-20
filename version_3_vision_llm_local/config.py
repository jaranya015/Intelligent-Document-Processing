import os
from pathlib import Path
from dotenv import load_dotenv

# โหลดตัวแปรจากไฟล์ .env ที่อยู่นอกสุด
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Keys & Tokens
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
NGROK_URL = os.getenv("NGROK_URL", "")

# ตัวเลือกระบบสกัดข้อมูล (vision/text -> JSON)
#   "gemini" (ค่า default) -> ใช้ Google Gemini ผ่านเน็ต ฟรีตามโควตารายวัน แม่นยำกว่า
#   "local"                -> ใช้ Ollama บนเครื่อง ไม่ต้องมีเน็ต แต่ความแม่นยำต่ำกว่า
# สลับได้จาก .env โดยไม่ต้องแก้โค้ด:  EXTRACTION_BACKEND=local
EXTRACTION_BACKEND = os.getenv("EXTRACTION_BACKEND", "gemini").strip().lower()

# Relative Paths สำหรับสร้างไฟล์และโฟลเดอร์ใช้งาน
OUTPUT_DIR = BASE_DIR / "version_1_photo_with_camera" / "vision_llm_output"
EXCEL_PATH = OUTPUT_DIR / "receipts.xlsx"
TEMP_DIR = BASE_DIR / "temp_images"

# สร้างโฟลเดอร์รอไว้ถ้ายังไม่มี
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)