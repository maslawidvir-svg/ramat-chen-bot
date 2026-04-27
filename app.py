import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """אתה סוכן AI של בית כנסת רמת חן ברמת גן. אתה עונה בעברית בלבד.
הטון שלך: מקצועי, ידידותי, חברותי, חם וקצר.
ענה בקצרה - עד 5-6 שורות.

פרטי בית הכנסת:
כתובת: רמת חן 5, רמת גן
טלפון: 03-5744026 | 050-5500457
מייל: bh.ramat.chen@gmail.com
יונתן - מנהלן (050-5500457)

זמני תפילה:
שחרית חול: 06:30
שחרית שבת: מניין א 06:45 | מניין ב 08:00
קבלת שבת: 10 דקות אחרי כניסת שבת
מנחה שבת צהריים: 13:00 קיץ | 13:30 חורף
מנחה שבת ערב: דקה אחרי צאת שבת
מנחה חול: רבע שעה לפני השקיעה
ערבית חול: בסיום מנחה
ספר תורה: שני וחמישי בשחרית בלבד
אפליקציה לזמנים: בית הכנסת שלי, קוד 275332

תעריפי אולם לחבר קהילה:
- חול: 600 שח אולם | 1000 שח היכל ריבה
- שבת לכלל המתפללים: חינם
- קידוש פרטי שבת: 600 שח אולם | 1000 שח היכל ריבה
- ארוחות פרטיות שבת: 1500 שח היכל ריבה בלבד

תעריפי אולם לא חבר:
- חול: 1800 שח אולם | 4000 שח היכל ריבה
- שבת לכלל: 1800 שח אולם בלבד
- קידוש פרטי שבת: לא אפשרי

בר מצווה שני אולמות: 4500 שח
שיק ביטחון: 1500 שח
סיום אירוע: 22:30 פינוי עד 23:00
כשרות אורתודוקסית בלבד

תרומות - העברה בנקאית:
בנק דיסקונט 11, סניף מרום נוה 96
אגודת בית הכנסת רמת חן, חשבון 127415183

כשמישהו מדווח תקלה - אמור שהדיווח נרשם ויטופל. הוסף [TICKET] בסוף.
שאלות שלא קשורות - הפנה ליונתן 050-5500457"""

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if not incoming_msg:
        return str(MessagingResponse())

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        response = model.generate_content(incoming_msg)
        reply = response.text.strip()

        if "[TICKET]" in reply:
            reply = reply.replace("[TICKET]", "").strip()
            log_maintenance_ticket(sender, incoming_msg)

    except Exception as e:
        reply = "מצטערים, יש תקלה זמנית. צור קשר עם יונתן במספר 050-5500457"
        print(f"Error: {e}")

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

def log_maintenance_ticket(sender, description):
    import datetime
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"[תקלה] {now} | {sender} | {description}")

@app.route("/", methods=["GET"])
def home():
    return "בוט בית כנסת רמת חן פעיל"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
