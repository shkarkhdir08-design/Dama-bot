import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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

import io
import discord
from discord.ext import commands
from PIL import Image, ImageDraw

# --- GAME CONSTANTS ---
EMPTY = 0
WHITE = 1
BLACK = 2
WHITE_KING = 3
BLACK_KING = 4

# --- GAME LOGIC ---
class DamaGame:
    def __init__(self, player_white: discord.User, player_black: discord.User):
        self.p1 = player_white
        self.p2 = player_black
        self.turn = player_white
        self.board = self.create_board()
        self.selected = None  # (row, col)

    def create_board(self):
        board = [[EMPTY for _ in range(8)] for _ in range(8)]
        for r in range(1, 3):  # Black
            for c in range(8):
                board[r][c] = BLACK
        for r in range(5, 7):  # White
            for c in range(8):
                board[r][c] = WHITE
        return board

    def move_piece(self, start_r, start_c, end_r, end_c):
        piece = self.board[start_r][start_c]
        if piece == EMPTY:
            return False, "No piece at starting position."

        if self.turn == self.p1 and piece not in [WHITE, WHITE_KING]:
            return False, "Not your piece!"
        if self.turn == self.p2 and piece not in [BLACK, BLACK_KING]:
            return False, "Not your piece!"

        dr = end_r - start_r
        dc = end_c - start_c

        # Orthogonal check
        if abs(dr) > 0 and abs(dc) > 0:
            return False, "Diagonal moves are not allowed in Dama!"

        # Step Move (1 space)
        if abs(dr) + abs(dc) == 1:
            if self.board[end_r][end_c] != EMPTY:
                return False, "Target space is occupied."
            
            if piece == WHITE and dr > 0:
                return False, "White standard pieces cannot move backward!"
            if piece == BLACK and dr < 0:
                return False, "Black standard pieces cannot move backward!"

            self.board[end_r][end_c] = piece
            self.board[start_r][start_c] = EMPTY
            self.check_king(end_r, end_c)
            self.switch_turn()
            return True, "Moved successfully."

        # Capture Move (2 spaces)
        elif abs(dr) == 2 or abs(dc) == 2:
            mid_r = start_r + dr // 2
            mid_c = start_c + dc // 2
            mid_piece = self.board[mid_r][mid_c]

            if mid_piece == EMPTY:
                return False, "No piece to capture."
            if self.turn == self.p1 and mid_piece in [WHITE, WHITE_KING]:
                return False, "Cannot capture your own piece."
            if self.turn == self.p2 and mid_piece in [BLACK, BLACK_KING]:
                return False, "Cannot capture your own piece."
            if self.board[end_r][end_c] != EMPTY:
                return False, "Target space is occupied."

            self.board[end_r][end_c] = piece
            self.board[start_r][start_c] = EMPTY
            self.board[mid_r][mid_c] = EMPTY
            self.check_king(end_r, end_c)
            self.switch_turn()
            return True, "Captured piece!"

        return False, "Invalid move distance."

    def check_king(self, r, c):
        if self.board[r][c] == WHITE and r == 0:
            self.board[r][c] = WHITE_KING
        elif self.board[r][c] == BLACK and r == 7:
            self.board[r][c] = BLACK_KING

    def switch_turn(self):
        self.turn = self.p2 if self.turn == self.p1 else self.p1

# --- IMAGE GENERATOR (PIL) ---
def render_board_image(board, selected=None):
    cell_size = 60
    margin = 30
    img_size = cell_size * 8 + margin * 2
    
    img = Image.new("RGB", (img_size, img_size), "#2f3136")
    draw = ImageDraw.Draw(img)

    # Board colors
    light_square = "#e0c398"
    dark_square = "#a67c52"

    # Draw grid & labels
    for r in range(8):
        # Row & Column Labels
        draw.text((margin // 3, margin + r * cell_size + 20), str(r), fill="#ffffff")
        draw.text((margin + r * cell_size + 25, margin // 3), str(r), fill="#ffffff")

        for c in range(8):
            x1 = margin + c * cell_size
            y1 = margin + r * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size

            color = light_square if (r + c) % 2 == 0 else dark_square
            draw.rectangle([x1, y1, x2, y2], fill=color)

            # Highlight selected square
            if selected == (r, c):
                draw.rectangle([x1, y1, x2, y2], outline="#3b82f6", width=4)

            # Draw pieces
            piece = board[r][c]
            p_margin = 8
            px1, py1 = x1 + p_margin, y1 + p_margin
            px2, py2 = x2 - p_margin, y2 - p_margin

            if piece in [WHITE, WHITE_KING]:
                draw.ellipse([px1, py1, px2, py2], fill="#f8fafc", outline="#cbd5e1", width=2)
                if piece == WHITE_KING:
                    draw.text((x1 + 22, y1 + 18), "K", fill="#d97706")
            elif piece in [BLACK, BLACK_KING]:
                draw.ellipse([px1, py1, px2, py2], fill="#ef4444", outline="#b91c1c", width=2)
                if piece == BLACK_KING:
                    draw.text((x1 + 22, y1 + 18), "K", fill="#ffffff")

    # Save image to in-memory bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_games = {}

@bot.command()
async def dama(ctx, opponent: discord.User):
    """Starts a Dama game with a mentioned user: !dama @Friend"""
    if opponent.bot or opponent == ctx.author:
        await ctx.send("Please challenge a valid opponent!")
        return

    game = DamaGame(player_white=ctx.author, player_black=opponent)
    active_games[ctx.channel.id] = game

    image_bytes = render_board_image(game.board)
    file = discord.File(fp=image_bytes, filename="dama_board.png")

    msg = f"🎮 **DAMA GAME STARTED** 🎮\n⚪ White: {ctx.author.mention}\n🔴 Red: {opponent.mention}\n\n**Current Turn:** {game.turn.mention}"
    await ctx.send(msg, file=file)


@bot.command()
async def m(ctx, start_r: int, start_c: int, end_r: int, end_c: int):
    """Move command: !m <from_row> <from_col> <to_row> <to_col>"""
    game = active_games.get(ctx.channel.id)
    if not game:
        await ctx.send("No active Dama game in this channel. Start one with `!dama @user`!")
        return

    if ctx.author != game.turn:
        await ctx.send("It's not your turn!", delete_after=5)
        return

    success, msg = game.move_piece(start_r, start_c, end_r, end_c)
    if success:
        image_bytes = render_board_image(game.board)
        file = discord.File(fp=image_bytes, filename="dama_board.png")
        
        board_msg = f"**Current Turn:** {game.turn.mention}\nLast action: {msg}"
        await ctx.send(board_msg, file=file)
    else:
        await ctx.send(f"❌ **Invalid Move:** {msg}")

bot.run(os.getenv(''DISCORD_TOKEN"))

