import os
import io
import discord
from discord.ext import commands
from discord.ui import View, Button
from PIL import Image, ImageDraw
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- HEALTH CHECK FOR RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is live!")

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

Thread(target=run_web_server, daemon=True).start()

# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

EMPTY = 0
WHITE = 1
BLACK = 2
WHITE_KING = 3
BLACK_KING = 4

class DamaGame:
    def __init__(self, player_white: discord.User, player_black: discord.User):
        self.p1 = player_white
        self.p2 = player_black
        self.turn = player_white
        self.board = self.create_board()
        self.cursor = [5, 0]  # [row, col]
        self.selected_from = None

    def create_board(self):
        board = [[EMPTY for _ in range(8)] for _ in range(8)]
        for r in range(1, 3):
            for c in range(8):
                board[r][c] = BLACK
        for r in range(5, 7):
            for c in range(8):
                board[r][c] = WHITE
        return board

    def move_piece(self, sr, sc, er, ec):
        p = self.board[sr][sc]
        color = WHITE if self.turn == self.p1 else BLACK
        
        if p == EMPTY or (p in (WHITE, WHITE_KING) and color != WHITE) or (p in (BLACK, BLACK_KING) and color != BLACK):
            return False, "Not your piece!"

        dr = er - sr
        dc = ec - sc
        abs_dr, abs_dc = abs(dr), abs(dc)

        if p in (WHITE, BLACK):
            forward = -1 if color == WHITE else 1
            if abs_dr + abs_dc == 1:
                if dr == -forward:
                    return False, "Cannot move backward!"
                if self.board[er][ec] == EMPTY:
                    self.board[er][ec] = p
                    self.board[sr][sc] = EMPTY
                    self._check_king(er, ec)
                    return True, "Success"
            elif (abs_dr == 2 and dc == 0) or (abs_dc == 2 and dr == 0):
                mr, mc = (sr + er) // 2, (sc + ec) // 2
                mid_p = self.board[mr][mc]
                opp = (BLACK, BLACK_KING) if color == WHITE else (WHITE, WHITE_KING)
                if mid_p in opp and self.board[er][ec] == EMPTY:
                    self.board[er][ec] = p
                    self.board[sr][sc] = EMPTY
                    self.board[mr][mc] = EMPTY
                    self._check_king(er, ec)
                    return True, "Captured piece!"

        elif p in (WHITE_KING, BLACK_KING):
            if (dr == 0 or dc == 0) and self.board[er][ec] == EMPTY:
                step_r = 0 if dr == 0 else (1 if dr > 0 else -1)
                step_c = 0 if dc == 0 else (1 if dc > 0 else -1)
                curr_r, curr_c = sr + step_r, sc + step_c
                captured = []
                while (curr_r, curr_c) != (er, ec):
                    cp = self.board[curr_r][curr_c]
                    if cp != EMPTY:
                        opp = (BLACK, BLACK_KING) if color == WHITE else (WHITE, WHITE_KING)
                        if cp in opp:
                            captured.append((curr_r, curr_c))
                        else:
                            return False, "Blocked by own piece!"
                    curr_r += step_r
                    curr_c += step_c
                if len(captured) <= 1:
                    for cr, cc in captured:
                        self.board[cr][cc] = EMPTY
                    self.board[er][ec] = p
                    self.board[sr][sc] = EMPTY
                    return True, "King moved!"

        return False, "Invalid move!"

    def _check_king(self, r, c):
        if self.board[r][c] == WHITE and r == 0:
            self.board[r][c] = WHITE_KING
        elif self.board[r][c] == BLACK and r == 7:
            self.board[r][c] = BLACK_KING

def render_board_image(game: DamaGame):
    cell_size = 120  # High Definition resolution
    margin = 40
    img_size = cell_size * 8 + margin
    img = Image.new("RGB", (img_size, img_size), "#1E1E2E")
    draw = ImageDraw.Draw(img)

    for r in range(8):
        for c in range(8):
            x1 = margin + c * cell_size
            y1 = r * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size
            color = "#D18B47" if (r + c) % 2 == 1 else "#FFCE9E"
            draw.rectangle([x1, y1, x2, y2], fill=color)

            # Selected piece highlight (Green)
            if game.selected_from and game.selected_from == (r, c):
                draw.rectangle([x1+4, y1+4, x2-4, y2-4], outline="#2ECC71", width=8)

            # Cursor highlight (Yellow box)
            if game.cursor == [r, c]:
                draw.rectangle([x1+8, y1+8, x2-8, y2-8], outline="#F1C40F", width=6)

            piece = game.board[r][c]
            if piece != EMPTY:
                px1, py1 = x1 + 12, y1 + 12
                px2, py2 = x2 - 12, y2 - 12
                pcolor = "#FFFFFF" if piece in (WHITE, WHITE_KING) else "#E74C3C"
                draw.ellipse([px1, py1, px2, py2], fill=pcolor, outline="#000000", width=4)
                if piece in (WHITE_KING, BLACK_KING):
                    draw.ellipse([px1+24, py1+24, px2-24, py2-24], fill="#F1C40F")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

class DPadView(View):
    def __init__(self, game: DamaGame):
        super().__init__(timeout=None)
        self.game = game

    async def update_board_message(self, interaction: discord.Interaction, notice: str = ""):
        image_bytes = render_board_image(self.game)
        file = discord.File(fp=image_bytes, filename="dama_board.png")
        sel_text = f"\n📌 **Selected Piece:** Row {self.game.selected_from[0]}, Col {self.game.selected_from[1]}" if self.game.selected_from else ""
        content = f"**Current Turn:** {self.game.turn.mention}{sel_text}\n📍 **Cursor Position:** Row {self.game.cursor[0]}, Col {self.game.cursor[1]} {notice}"
        await interaction.response.edit_message(content=content, attachments=[file], view=self)

    async def move_cursor(self, interaction: discord.Interaction, dr: int, dc: int):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        self.game.cursor[0] = max(0, min(7, self.game.cursor[0] + dr))
        self.game.cursor[1] = max(0, min(7, self.game.cursor[1] + dc))
        await self.update_board_message(interaction)

    @discord.ui.button(label="⬆️ Up", style=discord.ButtonStyle.primary, row=0)
    async def up_btn(self, interaction: discord.Interaction, button: Button):
        await self.move_cursor(interaction, -1, 0)

    @discord.ui.button(label="⬅️ Left", style=discord.ButtonStyle.primary, row=1)
    async def left_btn(self, interaction: discord.Interaction, button: Button):
        await self.move_cursor(interaction, 0, -1)

    @discord.ui.button(label="➡️ Right", style=discord.ButtonStyle.primary, row=1)
    async def right_btn(self, interaction: discord.Interaction, button: Button):
        await self.move_cursor(interaction, 0, 1)

    @discord.ui.button(label="⬇️ Down", style=discord.ButtonStyle.primary, row=2)
    async def down_btn(self, interaction: discord.Interaction, button: Button):
        await self.move_cursor(interaction, 1, 0)

    @discord.ui.button(label="🎯 Select Piece", style=discord.ButtonStyle.secondary, row=3)
    async def select_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        r, c = self.game.cursor
        color = WHITE if self.game.turn == self.game.p1 else BLACK
        p = self.game.board[r][c]
        if p == EMPTY or (color == WHITE and p not in (WHITE, WHITE_KING)) or (color == BLACK and p not in (BLACK, BLACK_KING)):
            return await interaction.response.send_message("❌ Choose one of your own pieces!", ephemeral=True)
        self.game.selected_from = (r, c)
        await self.update_board_message(interaction, notice="\n✅ *Piece Selected! Now move cursor to destination and tap Confirm.*")

    @discord.ui.button(label="✅ Confirm Move", style=discord.ButtonStyle.success, row=3)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        if not self.game.selected_from:
            return await interaction.response.send_message("❌ Tap 'Select Piece' first!", ephemeral=True)

        sr, sc = self.game.selected_from
        er, ec = self.game.cursor
        success, msg = self.game.move_piece(sr, sc, er, ec)

        if success:
            self.game.turn = self.game.p2 if self.game.turn == self.game.p1 else self.game.p1
            self.game.selected_from = None
            await self.update_board_message(interaction)
        else:
            await interaction.response.send_message(f"❌ **Invalid Move:** {msg}", ephemeral=True)

@bot.command()
async def dama(ctx, opponent: discord.User):
    if opponent.bot:
        return await ctx.send("You cannot play against a bot!")
    game = DamaGame(ctx.author, opponent)
    image_bytes = render_board_image(game)
    file = discord.File(fp=image_bytes, filename="dama_board.png")
    view = DPadView(game)
    await ctx.send(f"🎮 **DAMA GAME STARTED** 🎮\n⚪ White: {ctx.author.mention}\n🔴 Red: {opponent.mention}\n\n**Current Turn:** {ctx.author.mention}\n📍 **Cursor Position:** Row 5, Col 0", file=file, view=view)

bot.run(os.getenv("DISCORD_TOKEN"))

