import os
import discord
from discord.ext import commands
from mam_hassan import generate_response, should_respond
from abilities import setup_abilities

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

    # Check if the message is intended for Mam Hassan chat persona
    is_reply = False
    if message.reference and message.reference.resolved:
        if message.reference.resolved.author.id == bot.user.id:
            is_reply = True

    if should_respond(message.content, bot.user.id, message.mentions, is_reply):
        async with message.channel.typing():
            reply = await generate_response(message.content)
            await message.reply(reply)

    # Process standard prefix commands (!play, !leave, etc.)
    await bot.process_commands(message)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN missing in environment variables!")

