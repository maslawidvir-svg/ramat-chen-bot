import os
import json
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
        creds_path = "/etc/secrets/GOOGLE_CREDENTIALS"
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"Calendar error: {e}")
        return None

def get_upcoming_events(days=60):
    service = get_calendar_service()
    if not service:
        return None
    try:
        now = datetime.datetime.utcnow()
        end = now + datetime.timedelta(days=days)
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            maxResults=30,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        print(f"Events error: {e}")
        return None

def format_events_for_prompt():
    events = get_upcoming_events()
    if events is None:
        return "לא הצלחתי לגשת ליומן כרגע."
    if not events:
        return "אין אירועים קרובים ביומן."
    lines = []
    for e in events:
        title = e.get("summary", "אירוע")
        start = e.get("start", {})
        date = start.get("date") or start.get("dateTime", "")[:10]
        lines.append(f"- {date}: {title}")
    return "\n".join(lines)

SYSTEM_PROMPT = """אתה יונתן, מנהלן בית כנסת רמת חן ברמת גן.
אתה עונה להודעות וואטסאפ בשם בית הכנסת.
הסגנון שלך: קצר, חם, טבעי - כמו בן אדם שעונה בוואטסאפ. לא רשמי מדי.
אל תפתח עם "שלום" בכל הודעה - תגיב כמו שאנשים מדברים בוואטסאפ.
אם אתה לא יודע משהו - תגיד בכנות ותפנה ליונתן האמיתי: 050-5500457.

פרטי בית הכנסת:
כתובת: רמת חן 5, רמת גן
טלפון: 03-5744026 | 050-5500457
מייל: bh.ramat.chen@gmail.com
אתר: www.bhrc.org.il

זמני תפילה:
שחרית חול: 06:30
שחרית שבת: מניין א' 06:45 | מניין ב' 08:00
קבלת שבת: 10 דקות אחרי כניסת שבת
מנחה שבת (צהריים): 13:00 קיץ | 13:30 חורף
מנחה שבת (ערב): דקה לפני צאת שבת
מנחה חול: רבע שעה לפני השקיעה
ערבית: בסיום מנחה
ספר תורה: שני וחמישי בשחרית
לזמנים מדויקים: אפליקציה "בית הכנסת שלי", קוד 275332

אולם היכל ריבה:
לחבר קהילה:
- חול: 600 ש"ח (אולם) | 1,000 ש"ח (היכל ריבה)
- שבת לכלל המתפללים: חינם
- קידוש פרטי שבת: 600 ש"ח | 1,000 ש"ח
- ארוחות פרטיות שבת: 1,500 ש"ח (היכל ריבה בלבד)
לא חבר:
- חול: 1,800 ש"ח | 4,000 ש"ח
- שבת לכלל: 1,800 ש"ח (אולם בלבד)
בר מצווה שני אולמות: 4,500 ש"ח
שיק ביטחון: 1,500 ש"ח
סיום: 22:30 | פינוי: 23:00
כשרות אורתודוקסית בלבד

תרומות - העברה בנקאית:
בנק דיסקונט 11 | סניף מרום נוה 96
אגודת בית הכנסת רמת חן | חשבון 127415183

כשמישהו מדווח תקלה - תגיד שרשמת ותטפל. הוסף [TICKET] בסוף.
שאלות שלא קשורות - הפנה ל-050-5500457"""

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
        "content": incoming_msg
    })

    if len(conversation_history[sender]) > 20:
        conversation_history[sender] = conversation_history[sender][-20:]

    # בדיקה אם השאלה קשורה לתאריכים פנויים
    calendar_keywords = ["פנוי", "תאריך", "זמין", "אפשר להזמין", "מתי אפשר", "האולם פנוי", "לבדוק"]
    needs_calendar = any(k in incoming_msg for k in calendar_keywords)

    system = SYSTEM_PROMPT
    if needs_calendar:
        events_text = format_events_for_prompt()
        system += f"\n\nאירועים קרובים ביומן (תאריכים תפוסים):\n{events_text}"

    try:
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
        reply = "סורי, יש תקלה קטנה כרגע. נסה שוב בעוד דקה או התקשר ל-050-5500457"
        print(f"Error: {e}")

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

def log_ticket(sender, description):
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"[תקלה] {now} | {sender} | {description}")

@app.route("/", methods=["GET"])
def home():
    return "בוט בית כנסת רמת חן פעיל ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
