import os
import random
import asyncio
import discord
from discord.ext import commands
import yt_dlp
import static_ffmpeg

# Initialize pre-compiled FFmpeg paths dynamically
static_ffmpeg.add_paths()

# --- WISDOM & TEA DATA ---
WISDOM_QUOTES = [
    "Patience is the key to everything, ganjo. You cannot rush the tea to boil faster.",
    "A smooth sea never made a skilled sailor, brakam. Take the loss in Dama and learn from it.",
    "Do not trust a man who drinks his tea cold or speaks too fast, kake.",
    "Respect your elders, work hard, and never leave your king unprotected!"
]

TEA_TYPES = ["Peshmerga-style strong black tea ☕", "Cardamom tea ☕", "Saffron tea ☕"]

# --- YOUTUBE-DLP & FFMPEG CONFIGURATION ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios']
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)

# --- USER NICKNAME MEMORY STORE ---
USER_NICKNAMES = {}

def assign_kurdish_nickname(user_id: int, interaction_style: str = "neutral") -> str:
    if user_id in USER_NICKNAMES:
        return USER_NICKNAMES[user_id]
    
    polite_nicks = ["Kakî Delal (Dear Brother)", "Gula Ser Dilan (Flower of Hearts)", "Dostê Piştrast (Trustworthy Friend)"]
    funny_nicks = ["Serqeşmer (Joker / Playful One)", "Şêrê Ser Taktê (King of the Table)", "Serreq (Stubborn One)"]
    casual_nicks = ["Kuri Qoz (Handsome Lad)", "Ganjo (Youngster)", "Bra Biçuk (Little Brother)"]

    if "polite" in interaction_style or "kind" in interaction_style:
        nick = random.choice(polite_nicks)
    elif "stubborn" in interaction_style or "funny" in interaction_style:
        nick = random.choice(funny_nicks)
    else:
        nick = random.choice(casual_nicks)

    USER_NICKNAMES[user_id] = nick
    return nick

# --- SETUP DISCORD BOT ABILITIES ---
def setup_abilities(bot: commands.Bot):

    # 1. WELCOME NEW MEMBERS
    @bot.event
    async def on_member_join(member):
        channel = member.guild.system_channel
        if channel and channel.permissions_for(member.guild.me).send_messages:
            welcome_msgs = [
                f"Baxêr bêt, {member.mention}! Welcome to the server, giyan! Sit down, relax, and let Mam Hassan pour you some tea ☕.",
                f"Ahlan wa sahlan, {member.mention}! Step inside, kake. Don't be shy, we were just about to start a game of Dama!",
                f"Look who arrived! Welcome {member.mention}, gulê! Make yourself at home in our server."
            ]
            await channel.send(random.choice(welcome_msgs))

    # 2. VOICE & MUSIC COMMANDS
    @bot.command(name="join")
    async def join_vc(ctx):
        """ Joins the user's current Voice Channel. """
        if not ctx.author.voice:
            return await ctx.send("Wallah you are not in a voice channel, kake! Join one first.")
        
        channel = ctx.author.voice.channel
        try:
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect(timeout=60.0, reconnect=True)
            await ctx.send(f"🔊 Joined **{channel.name}**! What song are we listening to today, ganjo?")
        except Exception as e:
            print(f"Voice Join Error: {e}")
            await ctx.send(f"Wallah I couldn't step into the voice room! Error: {e}")

    @bot.command(name="play")
    async def play_music(ctx, *, search_query: str):
        """ Searches and plays any song from YouTube. """
        if not ctx.author.voice:
            return await ctx.send("You need to be in a Voice Channel to play music, brakam!")

        if not ctx.voice_client:
            try:
                await ctx.author.voice.channel.connect(timeout=60.0, reconnect=True)
            except Exception as e:
                return await ctx.send(f"Could not connect to voice channel: {e}")

        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(search_query, loop=bot.loop, stream=True)
                
                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()

                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                await ctx.send(f"🎶 **Now Playing:** {player.title}\nEnjoy the music, giyan!")
            except Exception as e:
                print(f"Music error: {e}")
                await ctx.send(f"Wallah I couldn't stream that track! Details: {e}")

    @bot.command(name="stop")
    async def stop_music(ctx):
        """ Stops playing audio. """
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Stopped the music, kake!")
        else:
            await ctx.send("No music is currently playing, ganjo.")

    @bot.command(name="leave")
    async def leave_vc(ctx):
        """ Leaves the current voice channel. """
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Left the voice channel. Call me whenever you want more music or tea!")
        else:
            await ctx.send("I am not in a voice channel, kake.")

    # 3. EXTRA UTILITY COMMANDS
    @bot.command(name="nickname")
    async def get_my_nickname(ctx):
        nick = assign_kurdish_nickname(ctx.author.id)
        await ctx.send(f"To me, you will always be **{nick}**, {ctx.author.mention}!")

    @bot.command(name="wisdom")
    async def wisdom_cmd(ctx):
        quote = random.choice(WISDOM_QUOTES)
        await ctx.send(f"📜 *Mam Hassan stroking his beard:* \"{quote}\"")

    @bot.command(name="tea")
    async def tea_cmd(ctx, member: discord.Member = None):
        target = member or ctx.author
        tea = random.choice(TEA_TYPES)
        await ctx.send(f"Here, {target.mention}, sit down and take a cup of {tea}. Drink up, giyan!")

    # 4. DAMA (CHECKERS) COMMAND
    @bot.command(name="dama")
    async def dama_cmd(ctx, opponent: discord.Member = None):
        """ Starts a game of Kurdish Dama / Checkers. """
        if opponent is None:
            return await ctx.send("Wallah ganjo, you need to challenge someone! Use: `!dama @username`")
        
        if opponent.id == ctx.author.id:
            return await ctx.send("You cannot play Dama against yourself, kake! Challenge a friend.")
            
        if opponent.bot:
            return await ctx.send("Playing Dama against a bot? Let a real human face your skills first, brakam!")

        await ctx.send(
            f"🎲 **Dama Game Started!** 🎲\n"
            f"{ctx.author.mention} has challenged {opponent.mention} to a match of Kurdish Dama!\n"
            f"Mam Hassan is pouring the tea while watching the board ☕. Good luck!"
        )

