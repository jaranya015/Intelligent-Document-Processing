import uuid
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob,
    PushMessageRequest, TextMessage, FlexMessage, FlexContainer
)
from linebot.v3.webhooks import MessageEvent, ImageMessageContent, PostbackEvent

from version_3_vision_llm import config
from version_3_vision_llm.extract_receipt_local import extract_receipt_data
from version_3_vision_llm.excel_writer import append_receipt_to_excel
from version_3_vision_llm.line_flex import create_receipt_flex

app = FastAPI()

configuration = Configuration(access_token=config.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(config.LINE_CHANNEL_SECRET)

PENDING_CONFIRMS = {}

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = (await request.body()).decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"

@handler.add(MessageEvent)
def handle_message_event(event: MessageEvent):
    if not isinstance(event.message, ImageMessageContent):
        return

    message_id = event.message.id
    user_id = event.source.user_id  # ดึง User ID ไว้ใช้ Push Message ย้อนหลัง
    
    # 1. ดาวน์โหลดรูปภาพ
    with ApiClient(configuration) as api_client:
        blob_api = MessagingApiBlob(api_client)
        content = blob_api.get_message_content(message_id)
        
        temp_img_path = config.TEMP_DIR / f"{message_id}.jpg"
        with open(temp_img_path, "wb") as f:
            f.write(content)

    # 2. แจ้งผู้ใช้เบื้องต้นว่ากำลังประมวลผล
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text="⏳ กำลังอ่านข้อมูลใบเสร็จ กรุณารอสักครู่...")]
            )
        )

    # 3. สกัดข้อมูลผ่าน Local LLM (แม้จะใช้เวลานานก็ไม่หลุด Token)
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
        
        # ส่ง Flex Message กลับผ่าน Push API
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[flex_msg]
                )
            )
    except Exception as e:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=f"❌ อ่านใบเสร็จไม่สำเร็จ: {str(e)}")]
                )
            )

@handler.add(PostbackEvent)
def handle_postback(event: PostbackEvent):
    data_str = event.postback.data
    user_id = event.source.user_id
    params = dict(p.split("=") for p in data_str.split("&"))

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

        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=reply_text)]
                )
            )