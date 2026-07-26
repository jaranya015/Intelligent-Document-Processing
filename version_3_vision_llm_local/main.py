import uuid
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob,
    PushMessageRequest, TextMessage, FlexMessage, FlexContainer, ImageMessage
)
from linebot.v3.webhooks import MessageEvent, ImageMessageContent, TextMessageContent, PostbackEvent

from version_3_vision_llm_local import config
from version_3_vision_llm_local.extract_receipt_local import (
    extract_receipt_data,
    extract_text_to_json
)
from version_3_vision_llm_local.excel_writer import append_receipt_to_excel
from version_3_vision_llm_local.line_flex import create_receipt_flex, create_menu_flex
from version_3_vision_llm_local.document_generator import generate_document_image

from datetime import datetime

app = FastAPI()

# Middleware ข้ามหน้าเตือน ngrok
class NgrokBypassMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

app.add_middleware(NgrokBypassMiddleware)

configuration = Configuration(access_token=config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(config.LINE_CHANNEL_SECRET)

PENDING_CONFIRMS = {}
USER_MODES = {}  # เก็บ State โหมดของผู้ใช้ {user_id: mode}

# Mount ให้เข้าถึงไฟล์รูปภาพ static
app.mount("/static", StaticFiles(directory=config.BASE_DIR / "static"), name="static")

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")

    try:
        # สั่งให้ทำงานเบื้องหลัง เพื่อให้ FastAPI ตอบกลับ LINE ทันทีใน 0.1 วินาที
        background_tasks.add_task(handler.handle, body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"

def send_push_text(user_id: str, text: str):
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.push_message(
            PushMessageRequest(to=user_id, messages=[TextMessage(text=text)])
        )

# --- 1. จัดการข้อความ (Text และ Image) ทั้งหมดใน Event เดียว ---
@handler.add(MessageEvent)
def handle_message_event(event: MessageEvent):
    user_id = event.source.user_id

    # CASE A: ผู้ใช้ส่งข้อความตัวอักษร
    if isinstance(event.message, TextMessageContent):
        text = event.message.text.strip()
        
        # พิมพ์เมนู
        if text.lower() in ["เมนู", "menu", "hi", "hello"]:
            flex_dict = create_menu_flex()
            flex_msg = FlexMessage(
                alt_text=flex_dict["altText"],
                contents=FlexContainer.from_dict(flex_dict["contents"])
            )
            with ApiClient(configuration) as api_client:
                messaging_api = MessagingApi(api_client)
                messaging_api.push_message(PushMessageRequest(to=user_id, messages=[flex_msg]))
            return

        # ตรวจสอบโหมดปัจจุบัน
        current_mode = USER_MODES.get(user_id, "receipt")
        
        if current_mode in ["invoice", "quotation", "po", "tax_invoice"]:
            send_push_text(user_id, "⏳ กำลังประมวลผลและสร้างรูปเอกสาร...")
            
            try:
                # 1. แปลงข้อความสั่งซื้อเป็น JSON ด้วย LLM
                doc_data = extract_text_to_json(text)
                
                # 2. บันทึกลง Excel
                append_receipt_to_excel(doc_data, str(config.EXCEL_PATH), source_file=f"Generated_{current_mode}")
                
                # 3. สร้างรูปเอกสารจาก Template PNG
                template_file = f"{current_mode}_template.jpg"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_file = f"{current_mode}_{timestamp}_{user_id[:6]}.jpg"
                
                generate_document_image(current_mode, doc_data, template_file, out_file)
                
                # 4. ส่งรูปภาพกลับให้ User
                image_url = f"{config.NGROK_URL}/static/generated_docs/{out_file}?ngrok-skip-browser-warning=true"
                img_msg = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
                
                with ApiClient(configuration) as api_client:
                    messaging_api = MessagingApi(api_client)
                    messaging_api.push_message(PushMessageRequest(to=user_id, messages=[img_msg]))
            except Exception as e:
                send_push_text(user_id, f"❌ เกิดข้อผิดพลาดในการสร้างเอกสาร: {str(e)}")

    # CASE B: ผู้ใช้ส่งรูปภาพเข้ามา
    elif isinstance(event.message, ImageMessageContent):
        current_mode = USER_MODES.get(user_id, "receipt")
        if current_mode == "receipt":
            handle_receipt_image(event, user_id)
        else:
            send_push_text(user_id, "📌 โหมดนี้รองรับการพิมพ์ข้อความสั่งออกเอกสารครับ")

def handle_receipt_image(event: MessageEvent, user_id: str):
    message_id = event.message.id
    
    with ApiClient(configuration) as api_client:
        blob_api = MessagingApiBlob(api_client)
        content = blob_api.get_message_content(message_id)
        
        temp_img_path = config.TEMP_DIR / f"{message_id}.jpg"
        with open(temp_img_path, "wb") as f:
            f.write(content)

    send_push_text(user_id, "⏳ กำลังอ่านข้อมูลใบเสร็จ กรุณารอสักครู่...")

    try:
        data = extract_receipt_data(str(temp_img_path))
        temp_file_id = str(uuid.uuid4())[:8]
        PENDING_CONFIRMS[temp_file_id] = {
            "data": data,
            "source_file": f"{message_id}.jpg"
        }
        
        flex_dict = create_receipt_flex(data, temp_file_id)
        flex_msg = FlexMessage(
            alt_text=flex_dict["altText"],
            contents=FlexContainer.from_dict(flex_dict["contents"])
        )
        
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.push_message(
                PushMessageRequest(to=user_id, messages=[flex_msg])
            )
    except Exception as e:
        send_push_text(user_id, f"❌ อ่านใบเสร็จไม่สำเร็จ: {str(e)}")

# --- 2. จัดการเมื่อกดปุ่มบน Flex Message ---
@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent):
    data_str = event.postback.data
    user_id = event.source.user_id
    params = dict(p.split("=") for p in data_str.split("&"))

    if "mode" in params:
        mode = params["mode"]
        USER_MODES[user_id] = mode
        
        mode_names = {
            "receipt": "🧾 บันทึกข้อมูลใบเสร็จ/บัญชี",
            "invoice": "📄 ออกใบแจ้งหนี้ (Invoice)",
            "quotation": "📋 ออกใบเสนอราคา (Quotation)",
            "po": "🛍️ ออกใบสั่งซื้อ (PO)",
            "tax_invoice": "🏷️ ใบกำกับภาษี / ใบเสร็จรับเงิน"
        }
        send_push_text(user_id, f"✅ เลือกโหมด: {mode_names.get(mode, mode)}\nคุณสามารถพิมพ์ข้อมูลสั่งทำรายการเข้ามาได้เลยครับ")
        return

    if params.get("action") == "confirm":
        file_id = params.get("file_id")
        pending = PENDING_CONFIRMS.pop(file_id, None)

        if pending:
            append_receipt_to_excel(
                data=pending["data"],
                excel_path=str(config.EXCEL_PATH),
                source_file=pending["source_file"]
            )
            reply_text = "✅ บันทึกข้อมูลลงไฟล์ Excel เรียบร้อยแล้วครับ!"
        else:
            reply_text = "⚠️ รายการนี้ถูกบันทึกไปแล้ว หรือรายการหมดอายุ"

        send_push_text(user_id, reply_text)