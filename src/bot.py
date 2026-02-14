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
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Nova is online as {bot.user}")


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


@bot.tree.command(name="nfl_predictions", description="Get NFL predictions for today")
async def nfl_predictions(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        games = fetch_today_games()

        if not games:
            await interaction.followup.send("No games today.")
            return

        embed = discord.Embed(
            title="🔥 Nova NFL Predictions",
            color=discord.Color.red()
        )

        for g in games:
            prob = predict_game(
                24, 21,
                20, 23
            )

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


bot.run(TOKEN)

