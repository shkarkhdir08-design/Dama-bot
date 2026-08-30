import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from mam_hassan import generate_response, should_respond
from abilities import setup_abilities

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

setup_abilities(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} ({bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    is_reply = False
    if message.reference and message.reference.resolved:
        if message.reference.resolved.author.id == bot.user.id:
            is_reply = True

    if should_respond(message.content, bot.user.id, message.mentions, is_reply):
        async with message.channel.typing():
            reply = await generate_response(message.content)
            await message.reply(reply)

    await bot.process_commands(message)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()

    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN missing in environment variables!")

