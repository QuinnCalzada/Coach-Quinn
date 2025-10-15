# bot.py
import os, json
import discord
from discord import app_commands
from discord.ext import commands
from openai import OpenAI
import sheets

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
QA_CHANNEL_ID = int(os.getenv("QA_CHANNEL_ID", "0"))

oa = OpenAI(api_key=OPENAI_API_KEY)

# Load personality once
with open("personality.json","r",encoding="utf-8") as f:
    P = json.load(f)

SYSTEM_PROMPT = (
    f"You are {P['name']}, {P['role']}. "
    f"Background: {P['background']} "
    f"Tone: {P['tone']} "
    f"Philosophy: {', '.join(P['philosophy'])}. "
    f"Rules: {', '.join(P['rules'])}. "
    f"Style cues: success={P['style']['success']} | failure={P['style']['failure']} | burnout={P['style']['burnout']}. "
    f"Use vocabulary when fitting: {', '.join(P['vocabulary'])}. "
    "Be concise, tactical, and specific. Protect the mission from overtraining."
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

async def check_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel_id != QA_CHANNEL_ID:
        await interaction.response.send_message(
            f"Use <#{QA_CHANNEL_ID}> for Coach Quinn commands.", ephemeral=True
        )
        return False
    return True

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Coach Quinn bot online as {bot.user}")

@bot.tree.command(name="ask", description="Ask Coach Quinn anything about training, recovery, mindset.")
async def ask(interaction: discord.Interaction, question: str):
    if not await check_channel(interaction): return
    user_msg = f"Question: {question}\nAnswer with clear actions. If relevant, reference Quinn's rowing training structure."
    resp = oa.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.5,
        messages=[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user","content":user_msg}]
    )
    await interaction.response.send_message(resp.choices[0].message.content[:1800])

@bot.tree.command(name="log", description="Log a workout to the Google Sheet.")
async def log_cmd(
    interaction: discord.Interaction,
    type: str,
    details: str,
    avg_hr: str = "",
    avg_split: str = "",
    meters: str = "",
    rpe: str = "",
    notes: str = ""
):
    if not await check_channel(interaction): return
    from datetime import date
    row = {
        "Date": str(date.today()),
        "Type": type,
        "Details": details,
        "Avg_HR": avg_hr,
        "Avg_Split": avg_split,
        "Meters": meters,
        "RPE": rpe,
        "Notes": notes
    }
    sheets.append_session(row)
    await interaction.response.send_message(f"Logged: **{type}** – {details}")

bot.run(DISCORD_BOT_TOKEN)
