import os
import asyncio
import discord
from discord.ext import commands
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import your custom modules
from dama_game import DamaGame, render_board_image, DPadView
from mam_hassan import should_respond, generate_response
from abilities import setup_abilities

# --- SELF-HEAVY AUTO-RESTARTING WEB SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Mam Hassan is active, listening, and healthy!")
        
    def log_message(self, format, *args):
        return  # Suppress standard HTTP web server console logs

def run_web_server():
    """ Keeps the web server running continuously. Restarts automatically if it crashes. """
    port = int(os.getenv("PORT", 10000))
    while True:
        try:
            server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
            print(f"🌐 Keep-alive web server active on port {port}")
            server.serve_forever()
        except Exception as e:
            print(f"⚠️ Web server encountered an error: {e}. Self-restarting in 5 seconds...")
            asyncio.run(asyncio.sleep(5))

# Start background server thread for Render 24/7 uptime
Thread(target=run_web_server, daemon=True).start()

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for welcoming new members
intents.voice_states = True  # Required for music & voice channels

bot = commands.Bot(command_prefix="!", intents=intents)

# Register abilities module (Welcome, Music, Tea, Wisdom, Nicknames)
setup_abilities(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}! Mam Hassan is officially online.")

# --- DAMA GAME COMMAND ---
@bot.command(name="dama")
async def start_dama(ctx, opponent: discord.User):
    """ Starts a game of Dama (Turkish Draughts) between two players. """
    if opponent.bot:
        return await ctx.send("Wallah you cannot play against a bot, kake!")
    if opponent == ctx.author:
        return await ctx.send("You cannot play against yourself, ganjo!")

    game = DamaGame(ctx.author, opponent)
    image_bytes = render_board_image(game)
    file = discord.File(fp=image_bytes, filename="dama_board.png")
    view = DPadView(game)
    
    await ctx.send(
        f"🎮 **DAMA GAME STARTED** 🎮\n⚪ White: {ctx.author.mention}\n🔴 Red: {opponent.mention}\n\n**Current Turn:** {ctx.author.mention}", 
        file=file, 
        view=view
    )

# --- RESILIENT AI CHAT EVENT LISTENER ---
@bot.event
async def on_message(message):
    """ Handles messages and responds with Gemini AI when Mam Hassan is mentioned or replied to. """
    if message.author.bot:
        return

    is_reply = False
    if message.reference:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author == bot.user:
                is_reply = True
        except Exception:
            pass

    # Check if Mam Hassan or Hassan was mentioned or tagged
    if should_respond(message.content, bot.user.id, message.mentions, is_reply):
        async with message.channel.typing():
            try:
                reply_text = await generate_response(message.content)
                await message.reply(reply_text)
            except Exception as e:
                print(f"⚠️ Error processing AI chat response: {e}")
                await message.reply("Wallah my brain went foggy for a second, ask me again kake!")

    # Execute traditional prefixed commands like !dama, !play, !tea
    await bot.process_commands(message)

# --- BOT RUNNER WITH RECOVERY LOOP ---
async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Error: DISCORD_TOKEN environment variable not set!")
        return

    while True:
        try:
            await bot.start(token)
        except Exception as e:
            print(f"⚠️ Connection dropped due to error: {e}. Reconnecting in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
