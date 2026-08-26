import os
import io
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
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
        self.selected_from = None
        self.selected_to = None

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

        # Basic movement validation
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

def render_board_image(board):
    cell_size = 60
    margin = 30
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

            piece = board[r][c]
            if piece != EMPTY:
                px1, py1 = x1 + 6, y1 + 6
                px2, py2 = x2 - 6, y2 - 6
                pcolor = "#FFFFFF" if piece in (WHITE, WHITE_KING) else "#E74C3C"
                draw.ellipse([px1, py1, px2, py2], fill=pcolor, outline="#000000", width=2)
                if piece in (WHITE_KING, BLACK_KING):
                    draw.ellipse([px1+12, py1+12, px2-12, py2-12], fill="#F1C40F")

    for i in range(8):
        draw.text((margin / 2 - 4, i * cell_size + 20), str(i), fill="#FFFFFF")
        draw.text((margin + i * cell_size + 25, img_size - 20), str(i), fill="#FFFFFF")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

active_games = {}

class DamaView(View):
    def __init__(self, game: DamaGame):
        super().__init__(timeout=None)
        self.game = game
        self.update_selects()

    def update_selects(self):
        self.clear_items()
        
        # Piece selection menu
        color = WHITE if self.game.turn == self.game.p1 else BLACK
        valid_pieces = []
        for r in range(8):
            for c in range(8):
                p = self.game.board[r][c]
                if (color == WHITE and p in (WHITE, WHITE_KING)) or (color == BLACK and p in (BLACK, BLACK_KING)):
                    valid_pieces.append(discord.SelectOption(label=f"Row {r}, Col {c}", value=f"{r},{c}"))

        piece_select = Select(placeholder="1. Select Piece to Move", options=valid_pieces[:25], custom_id="piece_select")
        piece_select.callback = self.on_piece_select
        self.add_item(piece_select)

        # Target selection menu
        targets = [discord.SelectOption(label=f"Row {r}, Col {c}", value=f"{r},{c}") for r in range(8) for c in range(8)]
        target_select = Select(placeholder="2. Select Destination", options=targets[:25], custom_id="target_select")
        target_select.callback = self.on_target_select
        self.add_item(target_select)

        # Move button
        btn = Button(label="Confirm Move", style=discord.ButtonStyle.success, custom_id="confirm_move")
        btn.callback = self.on_confirm
        self.add_item(btn)

    async def on_piece_select(self, interaction: discord.Interaction):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        val = interaction.data['values'][0]
        self.game.selected_from = tuple(map(int, val.split(',')))
        await interaction.response.send_message(f"Selected piece at Row {self.game.selected_from[0]}, Col {self.game.selected_from[1]}", ephemeral=True)

    async def on_target_select(self, interaction: discord.Interaction):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        val = interaction.data['values'][0]
        self.game.selected_to = tuple(map(int, val.split(',')))
        await interaction.response.send_message(f"Selected target Row {self.game.selected_to[0]}, Col {self.game.selected_to[1]}", ephemeral=True)

    async def on_confirm(self, interaction: discord.Interaction):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        if not self.game.selected_from or not self.game.selected_to:
            return await interaction.response.send_message("Please select both a piece and a destination first!", ephemeral=True)

        sr, sc = self.game.selected_from
        er, ec = self.game.selected_to
        success, msg = self.game.move_piece(sr, sc, er, ec)

        if success:
            self.game.turn = self.game.p2 if self.game.turn == self.game.p1 else self.game.p1
            self.game.selected_from = None
            self.game.selected_to = None
            self.update_selects()
            
            image_bytes = render_board_image(self.game.board)
            file = discord.File(fp=image_bytes, filename="dama_board.png")
            board_msg = f"**Current Turn:** {self.game.turn.mention}"
            await interaction.response.edit_message(content=board_msg, attachments=[file], view=self)
        else:
            await interaction.response.send_message(f"❌ **Invalid Move:** {msg}", ephemeral=True)

@bot.command()
async def dama(ctx, opponent: discord.User):
    if opponent.bot:
        return await ctx.send("You cannot play against a bot!")
    game = DamaGame(ctx.author, opponent)
    active_games[ctx.channel.id] = game
    image_bytes = render_board_image(game.board)
    file = discord.File(fp=image_bytes, filename="dama_board.png")
    view = DamaView(game)
    await ctx.send(f"🎮 **DAMA GAME STARTED** 🎮\n⚪ White: {ctx.author.mention}\n🔴 Red: {opponent.mention}\n\n**Current Turn:** {ctx.author.mention}", file=file, view=view)

bot.run(os.getenv("DISCORD_TOKEN"))

