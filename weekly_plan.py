# weekly_plan.py
import os, json, datetime, pytz, requests
from dateutil.parser import parse as parse_dt
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL_PLANS")
TZ = os.getenv("TIMEZONE", "America/New_York")

client = OpenAI(api_key=OPENAI_API_KEY)

USE_SHEETS = bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") and os.getenv("SHEET_ID"))
if USE_SHEETS:
    import sheets

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def days_to_goal(goal_date_str):
    tz = pytz.timezone(TZ)
    today = datetime.datetime.now(tz).date()
    goal = parse_dt(goal_date_str).date()
    return (goal - today).days

def recent_sessions_from_source(days=14):
    if USE_SHEETS:
        return sheets.recent_sessions(days=days)
    else:
        log = load_json("log.json")
        out = []
        for s in log.get("sessions", []):
            out.append({
                "Date": s.get("date",""),
                "Type": s.get("type",""),
                "Details": s.get("details",""),
                "Avg_HR": s.get("avg_hr",""),
                "Avg_Split": s.get("avg_split",""),
                "Meters": s.get("meters",""),
                "RPE": s.get("rpe",""),
                "Notes": s.get("notes",""),
            })
        return out

def build_prompt(personality, log):
    athlete = log["athlete"]
    recents = recent_sessions_from_source(days=14)
    recent_text = "\n".join([
        f"- {r.get('Date','?')} | {r.get('Type','?')} | HR {r.get('Avg_HR','?')} | RPE {r.get('RPE','?')} | Notes: {r.get('Notes','')}"
        for r in recents
    ]) or "No recent sessions."
    days_left = days_to_goal(athlete["goal_date"])

    system = (
        f"You are {personality['name']}, {personality['role']}. "
        f"Background: {personality['background']} "
        f"Tone: {personality['tone']} "
        f"Philosophy: {', '.join(personality['philosophy'])}. "
        f"Rules: {', '.join(personality['rules'])}. "
        f"Style cues: success={personality['style']['success']} | "
        f"failure={personality['style']['failure']} | burnout={personality['style']['burnout']}. "
        f"Use vocabulary when fitting: {', '.join(personality['vocabulary'])}. "
        "Be concise, tactical, and specific. Protect the mission from overtraining."
    )

    user = f"""
Athlete: {athlete['name']}
Goal: Sub-{athlete['goal_2k_time']} 2k on {athlete['goal_date']} (days left: {days_left})
Stats: weight={athlete['weight_lb']} lb, VO2max={athlete['vo2max']}

Recent 14-day sessions:
{recent_text}

Task:
Design a Monday–Sunday weekly plan that progresses toward the 2k goal. Include:
- Session type each day (erg/threshold/UT2/sprints/weights)
- Exact prescriptions (duration, rate, HR targets, split targets vs 2k), warm-up/cool-down
- Adjust for recovery risk based on recent HR/RPE
- 1–2 key focus cues for the week
- A concrete checkpoint (e.g., 6k, 4x1k) if warranted

Format for Discord in clear markdown with headings for each day.
"""
    return system, user

def call_gpt(system, user):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.5,
        messages=[{"role":"system","content":system},{"role":"user","content":user}]
    )
    return resp.choices[0].message.content.strip()

def post_webhook(content):
    r = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"**📅 COACH QUINN — WEEK PLAN**\n{content}"}, timeout=20)
    r.raise_for_status()

def main():
    personality = load_json("personality.json")
    log = load_json("log.json")
    system, user = build_prompt(personality, log)
    output = call_gpt(system, user)
    post_webhook(output)

if __name__ == "__main__":
    main()
