import os
import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

CALENDAR_ID = "maslawi18@gmail.com"

def get_calendar_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            "/etc/secrets/GOOGLE_CREDENTIALS",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"Calendar error: {e}")
        return None

def get_upcoming_events():
    service = get_calendar_service()
    if not service:
        return "לא הצלחתי לגשת ליומן."
    try:
        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(days=90)
        result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = result.get("items", [])
        if not events:
            return "אין אירועים קרובים ביומן."
        lines = []
        for e in events:
            title = e.get("summary", "אירוע")
            start = e.get("start", {})
            date = start.get("date") or start.get("dateTime", "")[:10]
            lines.append(f"- {date}: {title}")
        return "\n".join(lines)
    except Exception as e:
        print(f"Events error: {e}")
        return "שגיאה בגישה ליומן."

SYSTEM_PROMPT = """אתה עונה בשם בית כנסת רמת חן ברמת גן בוואטסאפ.

חשוב מאוד: כתוב כמו בן אדם אמיתי שעונה בוואטסאפ.
- משפטים קצרים וטבעיים
- אין bold, אין כותרות, אין תבניות
- אימוג'י אחד לכל היותר אם מתאים
- אל תחזור על "שלום" בכל הודעה
- תגיב בצורה חמה אבל ישירה

פרטי בית הכנסת:
כתובת: רמת חן 5, רמת גן
טלפון: 03-5744026 | 050-5500457
מייל: bh.ramat.chen@gmail.com
אתר: www.bhrc.org.il
מנהלן: יונתן - 050-5500457

זמני תפילה:
שחרית חול: 06:30
שחרית שבת: מניין א 06:45 | מניין ב 08:00
קבלת שבת: 10 דקות אחרי כניסת שבת
מנחה שבת צהריים: 13:00 קיץ | 13:30 חורף
מנחה שבת ערב: דקה לפני צאת שבת
מנחה חול: רבע שעה לפני השקיעה
ערבית: בסיום מנחה
ספר תורה: שני וחמישי בשחרית
לזמנים מדויקים: אפליקציה "בית הכנסת שלי" קוד 275332

תעריפי אולם לחבר קהילה:
- חול: 600 שח אולם | 1000 שח היכל ריבה
- שבת לכלל המתפללים: חינם
- קידוש פרטי שבת: 600 שח | 1000 שח היכל ריבה
- ארוחות פרטיות שבת: 1500 שח היכל ריבה בלבד

תעריפי אולם לא חבר:
- חול: 1800 שח אולם | 4000 שח היכל ריבה
- שבת לכלל: 1800 שח אולם בלבד
- קידוש פרטי שבת: לא אפשרי

בר מצווה שני אולמות: 4500 שח
שיק ביטחון: 1500 שח
סיום אירוע: 22:30 | פינוי: 23:00
כשרות אורתודוקסית בלבד

תרומות - העברה בנקאית:
בנק דיסקונט 11 | סניף מרום נוה 96
אגודת בית הכנסת רמת חן | חשבון 127415183

כשמישהו מדווח תקלה - תגיד שרשמת ותטפל בהקדם. הוסף [TICKET] בסוף התגובה.
שאלות שלא קשורות - הפנה בחום ל-050-5500457"""

conversation_history = {}

def needs_calendar_check(msg):
    check = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        messages=[{"role": "user", "content": f"האם ההודעה הבאה עוסקת בתאריכים, זמינות מקום, הזמנת אולם, או בדיקת לוח זמנים? ענה רק כן או לא:\n{msg}"}]
    )
    return "כן" in check.content[0].text

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
        "content": incoming_msg
    })

    if len(conversation_history[sender]) > 20:
        conversation_history[sender] = conversation_history[sender][-20:]

    try:
        system = SYSTEM_PROMPT
        if needs_calendar_check(incoming_msg):
            events = get_upcoming_events()
            system += f"\n\nאירועים קרובים ביומן (תאריכים תפוסים):\n{events}"

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=system,
            messages=conversation_history[sender]
        )

        reply = response.content[0].text.strip()

        if "[TICKET]" in reply:
            reply = reply.replace("[TICKET]", "").strip()
            log_ticket(sender, incoming_msg)

        conversation_history[sender].append({
            "role": "assistant",
            "content": reply
        })

    except Exception as e:
        reply = "סורי, יש תקלה קטנה. נסה שוב או התקשר ל-050-5500457"
        print(f"Error: {e}")

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

def log_ticket(sender, description):
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"[תקלה] {now} | {sender} | {description}")

@app.route("/", methods=["GET"])
def home():
    return "בוט בית כנסת רמת חן פעיל"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
