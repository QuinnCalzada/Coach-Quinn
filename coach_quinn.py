import os, json, requests, datetime, pytz
from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TZ = os.getenv("TIMEZONE", "America/New_York")

client = OpenAI(api_key=OPENAI_API_KEY)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def days_to_goal(goal_date_str):
    tz = pytz.timezone(TZ)
    today = datetime.datetime.now(tz).date()
    goal = parse_dt(goal_date_str).date()
    return (goal - today).days

def recent_sessions(log, days=7):
    tz = pytz.timezone(TZ)
    today = datetime.datetime.now(tz).date()
    xs = []
    for s in log.get("sessions", []):
        try:
            d = parse_dt(s["date"]).date()
            if (today - d).days <= days:
                xs.append(s)
        except Exception:
            continue
    return xs

def build_prompt(personality, log):
    athlete = log["athlete"]
    recents = recent_sessions(log, days=7)
    days_left = days_to_goal(athlete["goal_date"])

    # Compact recent data for the prompt
    recent_text = "\n".join([
        f"- {s['date']} | {s.get('type','?')} | HR {s.get('avg_hr','?')} | RPE {s.get('rpe','?')} | Notes: {s.get('notes','')}"
        for s in recents
    ]) or "No recent sessions."

    system = (
        f"You are {personality['name']}, {personality['role']}. "
        f"Background: {personality['background']} "
        f"Tone: {personality['tone']} "
        f"Philosophy: {', '.join(personality['philosophy'])} "
        f"Rules: {', '.join(personality['rules'])} "
        f"Style cues: success={personality['style']['success']} | failure={personality['style']['failure']} | burnout={personality['style']['burnout']} "
        f"Use vocabulary when fitting: {', '.join(personality['vocabulary'])}. "
        "Be concise, tactical, and specific. Protect the mission from overtraining."
    )

    user = f"""
Athlete: {athlete['name']}
Goal: Sub-{athlete['goal_2k_time']} 2k on {athlete['goal_date']} (days left: {days_left})
Stats: weight={athlete['weight_lb']} lb, VO2max={athlete['vo2max']}, age={athlete['age']}

Recent sessions (7d):
{recent_text}

Task:
1) Generate TODAY's training plan (erg and/or lifting) with exact sets, reps, stroke rates, HR targets, and estimated target splits relative to 2k pace when appropriate. Include warm-up and cool-down.
2) Detect recovery risk from recent HR/RPE. If high, adjust plan (do not glorify overtraining).
3) Provide a short 'Coach Quinn' motivation message (1–2 lines).
4) Provide a session quality focus (1–2 bullets) that I can repeat during the session.
Format as Discord-friendly markdown with clear headings and bullets.
"""

    return system, user

def call_gpt(system, user):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # fast + capable; upgrade to a larger model if you like
        temperature=0.5,
        messages=[
            {"role":"system","content": system},
            {"role":"user","content": user}
        ]
    )
    return resp.choices[0].message.content.strip()

def post_to_discord(content):
    data = {"content": content}
    r = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=20)
    r.raise_for_status()

def main():
    personality = load_json("personality.json")
    log = load_json("log.json")
    system, user = build_prompt(personality, log)
    output = call_gpt(system, user)
    post_to_discord(output)

if __name__ == "__main__":
    main()
