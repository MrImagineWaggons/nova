from models import Base, User, LicenseKey
from datetime import datetime, timedelta, timezone
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
from nfl_model import calculate_win_probability
from odds import get_moneyline_odds
from nfl_model import calculate_ev

BANNER_URL = "https://cdn.discordapp.com/attachments/1105664211255820428/1472473158199017512/Starlogo.png?ex=6992b2fe&is=6991617e&hm=c27702c4694d0f0560b9b8808e463cd84193710d02ac3addebce07f4c4441ea8"

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

    print(f"Logged in as {bot.user}")
    print("Slash commands synced to guild.")


def has_active_subscription(user):
    if not user.plan_type or not user.expires_at:
        return False

    now = datetime.now(timezone.utc)

    # Ensure expires_at is timezone aware
    if user.expires_at.tzinfo is None:
        expires = user.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires = user.expires_at

    return now < expires

@bot.tree.command(name="status", guild=discord.Object(id=GUILD_ID))
async def status(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    db = SessionLocal()

    user = db.query(User).filter_by(discord_id=str(interaction.user.id)).first()

    if not user or not user.plan_type:
        await interaction.followup.send("❌ You do not have an active subscription.")
        db.close()
        return

    now = datetime.now(timezone.utc)

    expires = user.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    remaining = expires - now

    if remaining.total_seconds() <= 0:
        await interaction.followup.send("⚠️ Your subscription has expired.")
        db.close()
        return

    days = remaining.days
    hours = remaining.seconds // 3600

    embed = discord.Embed(
        title="📊 Subscription Status",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Plan",
        value=user.plan_type.upper(),
        inline=False
    )

    embed.add_field(
        name="Expires",
        value=expires.strftime("%Y-%m-%d %H:%M UTC"),
        inline=False
    )

    embed.add_field(
        name="Time Remaining",
        value=f"{days} days, {hours} hours",
        inline=False
    )

    await interaction.followup.send(embed=embed)

    db.close()

@bot.tree.command(name="reset_user", guild=discord.Object(id=GUILD_ID))
async def reset_user(interaction: discord.Interaction, target: discord.User):

    if interaction.user.id != YOUR_DISCORD_ID:
        await interaction.response.send_message("Not authorized.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    db = SessionLocal()

    user = db.query(User).filter_by(discord_id=str(target.id)).first()

    if not user:
        await interaction.followup.send("User not found in database.")
        db.close()
        return

    # Unbind any license key tied to this user
    keys = db.query(LicenseKey).filter_by(bound_discord_id=str(target.id)).all()

    for key in keys:
        key.bound_discord_id = None

    # Reset user subscription
    user.plan_type = None
    user.expires_at = None

    db.commit()
    db.close()

    await interaction.followup.send(
        f"✅ Reset subscription for {target.name}."
    )

# ESPN Fetch
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

        # Extract basic stats if available
        try:
            home_score = int(home_team.get("score", 0))
            away_score = int(away_team.get("score", 0))
        except:
            home_score = 21
            away_score = 21

        games.append({
            "home": home_name,
            "away": away_name,
            "home_ppg": home_score + 20,   # placeholder baseline
            "away_ppg": away_score + 20,
            "home_allowed": 20,
            "away_allowed": 20
        })

    return games

@bot.tree.command(name="login", guild=discord.Object(id=GUILD_ID))
async def login(interaction: discord.Interaction, key: str):

    await interaction.response.defer(ephemeral=True)

    db = SessionLocal()

    license_key = db.query(LicenseKey).filter_by(key_value=key).first()

    if not license_key:
        await interaction.followup.send("Invalid key.", ephemeral=True)
        db.close()
        return

    if license_key.bound_discord_id:
        await interaction.followup.send("Key already used.", ephemeral=True)
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

    plan_type = user.plan_type
    expires_at = user.expires_at

    db.close()

    await interaction.followup.send(
        f"✅ {plan_type.upper()} plan activated!\nExpires: {expires_at}",
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

        # 🔴 Premium Red Theme
        embed = discord.Embed(
            title="★ STAR PREDICTOR — NFL EDGE REPORT ★",
            description="Data > Emotion • Long-term EV > Short-term hype",
            color=0xB11226
        )

        embed.set_thumbnail(url=BANNER_URL)
        
        embed.set_author(
            name=f"{interaction.user.display_name}'s STAR Dashboard",
            icon_url=interaction.user.display_avatar.url
        )
      
        # User Display
        embed.set_author(
            name=f"{interaction.user.display_name}'s Betting Dashboard",
            icon_url=interaction.user.display_avatar.url
        )

        for g in games:

            prob = calculate_win_probability(
                g["home_ppg"],
                g["home_allowed"],
                g["away_ppg"],
                g["away_allowed"],
                home_field=True
            )

            odds_data = get_moneyline_odds(g["home"], g["away"])

            home_odds = None
            away_odds = None
            home_ev = None
            away_ev = None

            if odds_data:
                home_odds = odds_data.get(g["home"])
                away_odds = odds_data.get(g["away"])

            if home_odds:
                home_ev = calculate_ev(prob, home_odds)

            if away_odds:
                away_ev = calculate_ev(1 - prob, away_odds)

            # Determine Best Play
            best_pick = "No Positive EV Edge"
            ev_display = "N/A"

            if home_ev and home_ev > 0:
                best_pick = f"{g['home']} Moneyline ({home_odds})"
                ev_display = f"+{round(home_ev*100,2)}%"
            elif away_ev and away_ev > 0:
                best_pick = f"{g['away']} Moneyline ({away_odds})"
                ev_display = f"+{round(away_ev*100,2)}%"

            # Confidence Logic
            if prob >= 0.65:
                confidence = "High Confidence"
                risk = "Low Risk / Lower Payout"
                indicator = "🟢"
            elif prob >= 0.55:
                confidence = "Moderate Confidence"
                risk = "Balanced Risk"
                indicator = "🟡"
            else:
                confidence = "High Variance"
                risk = "Higher Risk / Higher Reward"
                indicator = "🔴"

            color_explain = {"🟢": "Strong edge detected",
                             "🟡": "Moderate edge",
                            "🔴": "High variance / upset potential"
                    }

            embed.add_field(
                name=f"{indicator} {g['home']} vs {g['away']}",
                value=(
                    f"📊 **Model Projection:** {g['home']} win probability {prob*100:.1f}%\n"
                    f"🎨 Indicator Meaning: {color_explain[indicator]}\n\n"
                    
                    f"💰 **Sportsbook Moneyline (FanDuel/DK Format)**\n"
                    f"• {g['home']}: {home_odds if home_odds else 'N/A'}\n"
                    f"• {g['away']}: {away_odds if away_odds else 'N/A'}\n\n"
                    
                     f"🔥 **Official STAR Pick:**\n"
                    f"➡️ {best_pick}\n\n"
                    f"📈 Expected Value (EV): {ev_display}\n"
                    f"🧠 Confidence Level: {confidence}\n"
                    f"⚖️ Risk–Reward: {risk}"
                ),
                inline=False
            )

        embed.set_footer(
            text="Moneyline = Pick team to win outright • EV = Expected profit over time • Bet responsibly"
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

