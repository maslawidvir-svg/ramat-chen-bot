import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """אתה סוכן AI של בית כנסת רמת חן ברמת גן. אתה עונה בעברית בלבד.
הטון שלך: מקצועי, ידידותי, חברותי, חם וקצר. אל תהיה פורמלי מדי.
ענה תמיד בקצרה - עד 5-6 שורות לכל היותר.

פרטי בית הכנסת:
כתובת: רמת חן 5, רמת גן
טלפון: 03-5744026 | 050-5500457
מייל: bh.ramat.chen@gmail.com
אתר: www.bhrc.org.il
יונתן - מנהלן בית הכנסת (050-5500457)

זמני תפילה:
שחרית חול: 06:30
שחרית שבת: מניין א' 06:45 | מניין ב' 08:00
קבלת שבת: 10 דקות אחרי כניסת שבת
מנחה שבת (צהריים): 13:00 קיץ | 13:30 חורף
מנחה שבת (ערב): דקה אחת אחרי צאת שבת
מנחה חול: רבע שעה לפני השקיעה (משתנה לפי תאריך)
ערבית חול: בסיום מנחה
הוצאת ספר תורה: ימי שני וחמישי בלבד, שחרית
לזמנים מדויקים: אפליקציה "בית הכנסת שלי", קוד: 275332

אולם היכל ריבה - תעריפי השכרה:
לחבר קהילה המשלם דמי חבר:
- אירוע ביום חול: 600 ש"ח (אולם בית הכנסת) | 1,000 ש"ח (היכל ריבה)
- אירוע שבת לכלל המתפללים: ללא תשלום
- קידוש פרטי בשבת: 600 ש"ח (אולם) | 1,000 ש"ח (היכל ריבה)
- ארוחות פרטיות בשבת: לא רלוונטי (אולם) | 1,500 ש"ח (היכל ריבה)

למי שאינו משלם דמי חבר:
- אירוע ביום חול: 1,800 ש"ח (אולם) | 4,000 ש"ח (היכל ריבה)
- אירוע שבת לכלל המתפללים: 1,800 ש"ח (אולם) | לא אפשרי (היכל ריבה)
- קידוש פרטי / ארוחות בשבת: לא אפשרי

בר מצווה - שני האולמות יחד: 4,500 ש"ח
שיק ביטחון: 1,500 ש"ח (מוחזר בתום האירוע ללא נזקים)
סיום אירוע: עד 22:30 | פינוי: עד 23:00
כשרות אורתודוקסית בלבד
לתיאום: 050-5500457 (יונתן)

תרומות - העברה בנקאית:
בנק דיסקונט, מס' בנק: 11
סניף: מרום נוה, מס' סניף: 96
שם חשבון: אגודת בית הכנסת רמת חן
מספר חשבון: 127415183

דיווח תקלות תחזוקה:
כאשר מישהו מדווח על תקלה, אסוף תיאור ומיקום ואמור שהדיווח נרשם ויטופל בהקדם.
בסוף תגובתך הוסף בשורה חדשה: [TICKET]

חוקים חשובים:
1. עברית בלבד. קצר וחם - עד 6 שורות.
2. אל תמציא מידע שאין לך.
3. אם השאלה לא קשורה ל-4 הנושאים - הפנה ליונתן במספר 050-5500457.
4. אל תציע שירותים נוספים."""

conversation_history = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if not incoming_msg:
        return str(MessagingResponse())

    if sender not in conversation_history:
        conversation_history[sender] = model.start_chat(history=[])

    try:
        full_msg = f"{SYSTEM_PROMPT}\n\nהודעת המשתמש: {incoming_msg}"
        chat = conversation_history[sender]
        response = chat.send_message(full_msg if len(chat.history) == 0 else incoming_msg)
        reply = response.text

        if "[TICKET]" in reply:
            reply = reply.replace("[TICKET]", "").strip()
            log_maintenance_ticket(sender, incoming_msg)

    except Exception as e:
        reply = "מצטערים, יש תקלה זמנית. אנא נסה שוב או צור קשר עם יונתן במספר 050-5500457"
        print(f"Error: {e}")

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

def log_maintenance_ticket(sender, description):
    import datetime
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"[תקלה] {now} | מספר: {sender} | תיאור: {description}")

@app.route("/", methods=["GET"])
def home():
    return "בוט בית כנסת רמת חן פעיל"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
