def create_receipt_flex(data: dict, temp_file_id: str) -> dict:
    company = data.get("company") or "ไม่ระบุร้านค้า"
    total_val = data.get("total") or 0.0
    currency = data.get("currency") or "THB"
    total_str = f"{total_val:,.2f} {currency}"
    date = data.get("date") or "ไม่ระบุวันที่"
    doc_no = data.get("document_no") or "-"
    low_conf = data.get("low_confidence_fields") or []

    status_text = f"⚠️ จุดที่อ่านไม่ชัด: {', '.join(low_conf)}" if low_conf else "✅ อ่านข้อมูลครบถ้วน"
    status_color = "#E63946" if low_conf else "#2A9D8F"

    return {
        "type": "flex",
        "altText": f"ตรวจสอบใบเสร็จ {company} ยอด {total_str}",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🧾 ตรวจสอบข้อมูลใบเสร็จ", "weight": "bold", "size": "md", "color": "#1DB446"},
                    {"type": "text", "text": status_text, "size": "xs", "color": status_color, "margin": "sm"},
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "spacing": "sm",
                        "contents": [
                            {"type": "text", "text": f"ร้านค้า: {company}", "weight": "bold", "wrap": True},
                            {"type": "text", "text": f"วันที่: {date}", "size": "sm", "color": "#666666"},
                            {"type": "text", "text": f"เลขที่: {doc_no}", "size": "sm", "color": "#666666"},
                            {"type": "text", "text": f"ยอดรวม: {total_str}", "size": "xl", "weight": "bold", "color": "#111111"}
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1DB446",
                        "action": {
                            "type": "postback",
                            "label": "ถูกต้อง บันทึกเลย",
                            "data": f"action=confirm&file_id={temp_file_id}"
                        }
                    }
                ]
            }
        }
    }

def create_menu_flex() -> dict:
    return {
        "type": "flex",
        "altText": "เลือกบริการจัดการเอกสารบัญชี",
        "contents": {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "💼 บัญชี & เอกสารดิจิทัล", "weight": "bold", "size": "md", "color": "#1DB446"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": "กรุณาเลือกรายการที่ต้องการทำ:", "size": "sm", "color": "#666666", "margin": "xs"},
                    {
                        "type": "button", "style": "primary", "color": "#2A9D8F", "height": "sm",
                        "action": {"type": "postback", "label": "🧾 บันทึกใบเสร็จ / บิลซื้อ", "data": "mode=receipt"}
                    },
                    {
                        "type": "button", "style": "primary", "color": "#F4A261", "height": "sm",
                        "action": {"type": "postback", "label": "📄 ออกใบเสนอราคา (Quotation)", "data": "mode=quotation"}
                    },
                    {
                        "type": "button", "style": "primary", "color": "#E76F51", "height": "sm",
                        "action": {"type": "postback", "label": "📜 ออกใบแจ้งหนี้ (Invoice)", "data": "mode=invoice"}
                    },
                    {
                        "type": "button", "style": "primary", "color": "#457B9D", "height": "sm",
                        "action": {"type": "postback", "label": "🛍️ ออกใบสั่งซื้อ (PO)", "data": "mode=po"}
                    },
                    {
                        "type": "button", "style": "primary", "color": "#1D3557", "height": "sm",
                        "action": {"type": "postback", "label": "🏷️ ใบกำกับภาษี / ใบเสร็จรับเงิน", "data": "mode=tax_invoice"}
                    }
                ]
            }
        }
    }