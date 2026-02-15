from models import Base, User, LicenseKey
from datetime import datetime, timedelta, timezone
import os
import discord
import requests
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from db import engine, SessionLocal
from sqlalchemy import inspect
from license import generate_license_key
from nfl_model import calculate_win_probability, calculate_ev
from odds import get_moneyline_odds

BANNER_URL = "https://cdn.discordapp.com/attachments/1105664211255820428/1472473158199017512/Starlogo.png?ex=6992b2fe&is=6991617e&hm=c27702c4694d0f0560b9b8808e463cd84193710d02ac3addebce07f4c4441ea8"

GUILD_ID = 1472040289802911962
YOUR_DISCORD_ID = 1064643686257918022
ALLOWED_ADMIN_IDS = {
    1064643686257918022,  
    1102771558411423794    
}

Base.metadata.create_all(bind=engine)
inspector = inspect(engine)
print("TABLES:", inspector.get_table_names())

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN missing.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# UTILITIES
# =========================

def has_active_subscription(user):
    if not user.plan_type or not user.expires_at:
        return False

    now = datetime.now(timezone.utc)

    expires = user.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    return now < expires

def fetch_today_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    resp = requests.get(url, timeout=10)
    data = resp.json()

    games = []

    for event in data.get("events", []):
        comp = event["competitions"][0]
        home_team = comp["competitors"][0]
        away_team = comp["competitors"][1]

        home_name = home_team["team"]["displayName"]
        away_name = away_team["team"]["displayName"]

        games.append({
            "home": home_name,
            "away": away_name,
            "home_ppg": 24,
            "away_ppg": 21,
            "home_allowed": 20,
            "away_allowed": 22
        })

    return games

# =========================
# MENU SYSTEM
# =========================

class MainMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📊 Account", style=discord.ButtonStyle.secondary)
    async def account_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_account_info(interaction)

    @discord.ui.button(label="🔥 Top 3 EV Plays", style=discord.ButtonStyle.danger)
    async def top3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_top3(interaction)

    @discord.ui.button(label="🎯 Predict", style=discord.ButtonStyle.primary)
    async def predict_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_predict_menu(interaction)

    @discord.ui.button(label="📈 Performance", style=discord.ButtonStyle.success)
    async def performance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_performance(interaction)

# =========================
# MENU HANDLERS
# =========================

async def show_account_info(interaction):
    db = SessionLocal()
    user = db.query(User).filter_by(discord_id=str(interaction.user.id)).first()

    embed = discord.Embed(
        title="📊 STAR Account Overview",
        color=0xB11226
    )

    embed.set_thumbnail(url=BANNER_URL)

    embed.add_field(name="Plan", value=user.plan_type.upper(), inline=False)
    embed.add_field(name="Expires", value=user.expires_at.strftime("%Y-%m-%d %H:%M UTC"), inline=False)
    embed.add_field(name="Discord Username", value=interaction.user.name, inline=False)
    embed.add_field(name="Discord ID", value=interaction.user.id, inline=False)
    embed.add_field(name="License Bound", value="Yes", inline=False)

    await interaction.response.edit_message(embed=embed, view=MainMenuView())
    db.close()

async def show_top3(interaction):
    embed = discord.Embed(
        title="🔥 Today's Top 3 EV Plays",
        description="Highest expected value bets across all markets.",
        color=0xB11226
    )

    embed.set_thumbnail(url=BANNER_URL)

    embed.add_field(name="1️⃣ Loading...", value="Model integration coming next.", inline=False)

    await interaction.response.edit_message(embed=embed, view=MainMenuView())

async def show_performance(interaction):
    embed = discord.Embed(
        title="📈 Performance Tracker",
        description="ROI tracking coming soon.",
        color=0xB11226
    )

    embed.set_thumbnail(url=BANNER_URL)

    embed.add_field(name="Win Rate", value="Coming Soon", inline=True)
    embed.add_field(name="ROI", value="Coming Soon", inline=True)

    await interaction.response.edit_message(embed=embed, view=MainMenuView())

class SportSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="NFL"),
            discord.SelectOption(label="NBA"),
            discord.SelectOption(label="MLB"),
        ]
        super().__init__(placeholder="Select a sport...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Loading {self.values[0]} predictions...",
            ephemeral=True
        )

async def show_predict_menu(interaction):
    view = discord.ui.View()
    view.add_item(SportSelect())

    await interaction.response.edit_message(
        content="Choose a sport:",
        embed=None,
        view=view
    )

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="genkey", guild=discord.Object(id=GUILD_ID))
async def genkey(interaction: discord.Interaction, plan: str, days: int):

    if interaction.user.id not in ALLOWED_ADMIN_IDS:
        await interaction.response.send_message(
            "Not authorized.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    db = SessionLocal()

    key_value = generate_license_key(plan)  # ← FIXED

    new_key = LicenseKey(
        key_value=key_value,
        plan_type=plan.lower(),
        duration_days=days,
        bound_discord_id=None
    )

    db.add(new_key)
    db.commit()
    db.close()

    await interaction.followup.send(
        f"🔑 Key Generated:\n`{key_value}`\nPlan: {plan}\nDuration: {days} days",
        ephemeral=True
    )


@bot.tree.command(name="menu", guild=discord.Object(id=GUILD_ID))
async def menu(interaction: discord.Interaction):

    db = SessionLocal()
    user = db.query(User).filter_by(discord_id=str(interaction.user.id)).first()

    if not user or not has_active_subscription(user):
        await interaction.response.send_message("Subscription required.", ephemeral=True)
        db.close()
        return

    embed = discord.Embed(
        title="★ STAR PREDICTOR — CONTROL CENTER ★",
        description="Select a module below.",
        color=0xB11226
    )

    embed.set_thumbnail(url=BANNER_URL)

    embed.add_field(name="Active Plan", value=user.plan_type.upper(), inline=True)
    embed.add_field(name="Expires", value=user.expires_at.strftime("%Y-%m-%d"), inline=True)

    await interaction.response.send_message(embed=embed, view=MainMenuView(), ephemeral=True)
    db.close()

@bot.tree.command(name="login", guild=discord.Object(id=GUILD_ID))
async def login(interaction: discord.Interaction, key: str):

    await interaction.response.defer(ephemeral=True)

    db = SessionLocal()
    license_key = db.query(LicenseKey).filter_by(key_value=key).first()

    if not license_key:
        await interaction.followup.send("Invalid key.")
        db.close()
        return

    if license_key.bound_discord_id:
        await interaction.followup.send("Key already used.")
        db.close()
        return

    user = db.query(User).filter_by(discord_id=str(interaction.user.id)).first()

    if not user:
        user = User(discord_id=str(interaction.user.id), username=interaction.user.name)
        db.add(user)
        db.commit()
        db.refresh(user)

    user.plan_type = license_key.plan_type
    user.expires_at = datetime.utcnow() + timedelta(days=license_key.duration_days)
    license_key.bound_discord_id = str(interaction.user.id)

    db.commit()
    db.close()

    await interaction.followup.send("✅ Plan activated!", ephemeral=True)

    await menu(interaction)

bot.run(TOKEN)