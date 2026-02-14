from models import Base, User, LicenseKey
from datetime import datetime, timedelta
import os
import discord
import requests
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from predict_nfl import predict_game
from db import engine
from models import Base
from sqlalchemy import inspect
from license import generate_license_key
from models import LicenseKey
from db import SessionLocal
Base.metadata.create_all(bind=engine)

inspector = inspect(engine)
print("TABLES:", inspector.get_table_names())

load_dotenv()  # loads local .env if present (for your PC)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

print("Token exists:", bool(TOKEN))

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN missing.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

print("DB:", os.getenv("DATABASE_URL"))

# Sync commands
GUILD_ID = 1472040289802911962 # replace with your server ID

@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Nova is online as {bot.user}")

def has_active_subscription(user):
    if not user.plan_type:
        return False

    if not user.expires_at:
        return False

    if datetime.utcnow() > user.expires_at:
        return False

    return True

# ESPN Fetch
def fetch_today_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    resp = requests.get(url, timeout=10)
    data = resp.json()

    games = []
    for event in data.get("events", []):
        comp = event["competitions"][0]
        home = comp["competitors"][0]["team"]["displayName"]
        away = comp["competitors"][1]["team"]["displayName"]
        games.append({"home": home, "away": away})
    return games

@bot.tree.command(name="login", guild=discord.Object(id=GUILD_ID))
async def login(interaction, key: str):

    db = SessionLocal()

    license_key = db.query(LicenseKey).filter_by(key_value=key).first()

    if not license_key:
        await interaction.response.send_message("Invalid key.", ephemeral=True)
        db.close()
        return

    if license_key.bound_discord_id:
        await interaction.response.send_message("Key already used.", ephemeral=True)
        db.close()
        return

    user = db.query(User).filter_by(discord_id=str(interaction.user.id)).first()

    if not user:
        user = User(
            discord_id=str(interaction.user.id),
            username=interaction.user.name
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user.plan_type = license_key.plan_type
    user.expires_at = datetime.utcnow() + timedelta(days=license_key.duration_days)

    license_key.bound_discord_id = str(interaction.user.id)

    db.commit()
    db.close()

    await interaction.response.send_message(
        f"✅ {user.plan_type.upper()} plan activated!\nExpires: {user.expires_at}",
        ephemeral=True
    )


@bot.tree.command(name="nfl_predictions", description="Get NFL predictions for today!", guild=discord.Object(id=GUILD_ID))
async def nfl_predictions(interaction: discord.Interaction):

    db = SessionLocal()
    user = db.query(User).filter_by(discord_id=str(interaction.user.id)).first()

    if not user or not has_active_subscription(user):
        await interaction.response.send_message("Subscription required.", ephemeral=True)
        db.close()
        return

    await interaction.response.defer(thinking=True)

    try:
        games = fetch_today_games()

        if not games:
            await interaction.followup.send("No games today.")
            db.close()
            return

        embed = discord.Embed(
            title="🔥 Nova NFL Predictions",
            color=discord.Color.red()
        )

        for g in games:
            prob = predict_game(24, 21, 20, 23)

            color_emoji = "🟢" if prob > 0.6 else "🟡" if prob > 0.5 else "🔴"

            embed.add_field(
                name=f"{g['home']} vs {g['away']}",
                value=f"{color_emoji} Home Win Probability: {prob*100:.1f}%",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print("Command error:", e)
        await interaction.followup.send("Something went wrong.")

    finally:
        db.close()

YOUR_DISCORD_ID = 1064643686257918022  # replace with yours

@bot.tree.command(name="generate_key", guild=discord.Object(id=GUILD_ID))
async def generate_key(interaction, plan: str):
    if interaction.user.id != YOUR_DISCORD_ID:
        await interaction.response.send_message("Not authorized.", ephemeral=True)
        return

    plan = plan.lower()

    if plan == "monthly":
        duration = 30
    elif plan == "trial":
        duration = 1
    else:
        await interaction.response.send_message("Invalid plan. Use: monthly or trial", ephemeral=True)
        return

    db = SessionLocal()

    key = generate_license_key(plan)

    new_key = LicenseKey(
        key_value=key,
        plan_type=plan,
        duration_days=duration
    )

    db.add(new_key)
    db.commit()
    db.close()

    await interaction.response.send_message(f"Generated {plan} key:\n`{key}`", ephemeral=True)

bot.run(TOKEN)

