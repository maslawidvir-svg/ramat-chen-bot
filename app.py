import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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
מנחה שבת צהריים: 13:00 קיץ | 13:30 חורף
מנחה שבת ערב: דקה אחת אחרי צאת שבת
מנחה חול: רבע שעה לפני השקיעה
ערבית חול: בסיום מנחה
הוצאת ספר תורה: ימי שני וחמישי בלבד בשחרית
לזמנים מדויקים: אפליקציה בית הכנסת שלי, קוד: 275332

אולם היכל ריבה - תעריפי השכרה:
לחבר קהילה המשלם דמי חבר:
- אירוע ביום חול: 600 שח אולם בית הכנסת | 1000 שח היכל ריבה
- אירוע שבת לכלל המתפללים: ללא תשלום
- קידוש פרטי בשבת: 600 שח אולם | 1000 שח היכל ריבה
- ארוחות פרטיות בשבת: לא רלוונטי אולם | 1500 שח היכל ריבה

למי שאינו משלם דמי חבר:
- אירוע ביום חול: 1800 שח אולם | 4000 שח היכל ריבה
- אירוע שבת לכלל המתפללים: 1800 שח אולם | לא אפשרי היכל ריבה
- קידוש פרטי וארוחות בשבת: לא אפשרי

בר מצווה שני האולמות יחד: 4500 שח
שיק ביטחון: 1500 שח מוחזר בתום האירוע
סיום אירוע: עד 22:30 פינוי עד 23:00
כשרות אורתודוקסית בלבד
לתיאום: 050-5500457 יונתן

תרומות העברה בנקאית:
בנק דיסקונט מספר 11
סניף מרום נוה מספר 96
שם חשבון: אגודת בית הכנסת רמת חן
מספר חשבון: 127415183

דיווח תקלות:
כשמישהו מדווח על תקלה אסוף תיאור ומיקום ואמור שהדיווח נרשם.
בסוף תגובתך הוסף: [TICKET]

חוקים:
1. עברית בלבד וקצר עד 6 שורות
2. אל תמציא מידע
3. שאלות שלא קשורות לאולם תרומה מידע או תקלה - הפנה ליונתן 050-5500457
4. אל תציע שירותים נוספים"""

conversation_history = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if not incoming_msg:
        return str(MessagingResponse())

    if sender not in conversation_history:
        conversation_history[sender] = []

    conversation_history[sender].append({
        "role": "user",
        "parts": [incoming_msg]
    })

    if len(conversation_history[sender]) > 20:
        conversation_history[sender] = conversation_history[sender][-20:]

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        chat = model.start_chat(history=conversation_history[sender][:-1])
        response = chat.send_message(incoming_msg)
        reply = response.text

        conversation_history[sender].append({
            "role": "model",
            "parts": [reply]
        })

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
