import io
import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont

EMPTY = 0
WHITE = 1
BLACK = 2
WHITE_KING = 3
BLACK_KING = 4

class DamaGame:
    def __init__(self, player_white: discord.User, player_black: discord.User):
        self.p1 = player_white  # White
        self.p2 = player_black  # Red/Black
        self.turn = player_white
        self.board = self.create_board()
        
        self.cursor_p1 = [5, 4]
        self.cursor_p2 = [2, 4]
        self.selected_from = None
        self.multi_jump_active = False

    @property
    def current_cursor(self):
        return self.cursor_p1 if self.turn == self.p1 else self.cursor_p2

    def create_board(self):
        board = [[EMPTY for _ in range(8)] for _ in range(8)]
        # Rows 1 and 2 filled with Black/Red
        for r in range(1, 3):
            for c in range(8):
                board[r][c] = BLACK
        # Rows 5 and 6 filled with White
        for r in range(5, 7):
            for c in range(8):
                board[r][c] = WHITE
        return board

    def get_piece_color(self, piece):
        if piece in (WHITE, WHITE_KING):
            return WHITE
        if piece in (BLACK, BLACK_KING):
            return BLACK
        return None

    def get_all_legal_captures_for_piece(self, board, r, c):
        """ Returns a list of all possible single-step capture destination coordinates from (r, c) """
        p = board[r][c]
        if p == EMPTY:
            return []
        
        color = self.get_piece_color(p)
        opp_color = BLACK if color == WHITE else WHITE
        captures = []
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)] # Up, Down, Left, Right

        if p in (WHITE, BLACK):
            forward = -1 if color == WHITE else 1
            for dr, dc in dirs:
                if dr == -forward:  # Regular men cannot capture backwards
                    continue
                mr, mc = r + dr, c + dc
                er, ec = r + 2 * dr, c + 2 * dc
                if 0 <= er < 8 and 0 <= ec < 8:
                    if self.get_piece_color(board[mr][mc]) == opp_color and board[er][ec] == EMPTY:
                        captures.append((er, ec, mr, mc))
                        
        elif p in (WHITE_KING, BLACK_KING):
            for dr, dc in dirs:
                curr_r, curr_c = r + dr, c + dc
                found_opp = None
                while 0 <= curr_r < 8 and 0 <= curr_c < 8:
                    cp = board[curr_r][curr_c]
                    cp_color = self.get_piece_color(cp)
                    if cp_color == color:
                        break
                    elif cp_color == opp_color:
                        if found_opp is not None:
                            break
                        found_opp = (curr_r, curr_c)
                    else:
                        if found_opp is not None:
                            captures.append((curr_r, curr_c, found_opp[0], found_opp[1]))
                    curr_r += dr
                    curr_c += dc
        return captures

    def move_piece(self, sr, sc, er, ec):
        p = self.board[sr][sc]
        color = WHITE if self.turn == self.p1 else BLACK
        opp_color = BLACK if color == WHITE else WHITE

        if self.get_piece_color(p) != color:
            return False, "Not your piece!", False

        dr = er - sr
        dc = ec - sc
        abs_dr, abs_dc = abs(dr), abs(dc)

        if dr != 0 and dc != 0:
            return False, "Movement must be orthogonal (straight lines)!", False

        # REGULAR MEN LOGIC
        if p in (WHITE, BLACK):
            forward = -1 if color == WHITE else 1
            
            # Simple step
            if abs_dr + abs_dc == 1 and not self.multi_jump_active:
                if dr == -forward:
                    return False, "Regular pieces cannot move backward!", False
                if self.board[er][ec] == EMPTY:
                    self.board[er][ec] = p
                    self.board[sr][sc] = EMPTY
                    self._check_king(er, ec)
                    return True, "Moved successfully.", False

            # Single Jump / Step in Multi-Jump
            elif (abs_dr == 2 and dc == 0) or (abs_dc == 2 and dr == 0):
                if dr == -forward * 2:
                    return False, "Regular pieces cannot capture backward!", False
                mr, mc = (sr + er) // 2, (sc + ec) // 2
                mid_p = self.board[mr][mc]
                if self.get_piece_color(mid_p) == opp_color and self.board[er][ec] == EMPTY:
                    self.board[er][ec] = p
                    self.board[sr][sc] = EMPTY
                    self.board[mr][mc] = EMPTY  # Immediate removal
                    self._check_king(er, ec)
                    
                    next_captures = self.get_all_legal_captures_for_piece(self.board, er, ec)
                    if len(next_captures) > 0:
                        return True, "Capture made! You can jump again.", True
                    return True, "Capture complete.", False

        # FLYING KING LOGIC
        elif p in (WHITE_KING, BLACK_KING):
            step_r = 0 if dr == 0 else (1 if dr > 0 else -1)
            step_c = 0 if dc == 0 else (1 if dc > 0 else -1)
            
            curr_r, curr_c = sr + step_r, sc + step_c
            captured_pos = None
            blocked = False

            while (curr_r, curr_c) != (er, ec):
                cp = self.board[curr_r][curr_c]
                cp_color = self.get_piece_color(cp)
                if cp_color == color:
                    blocked = True
                    break
                elif cp_color == opp_color:
                    if captured_pos is not None:
                        blocked = True
                        break
                    captured_pos = (curr_r, curr_c)
                curr_r += step_r
                curr_c += step_c

            if blocked or self.board[er][ec] != EMPTY:
                return False, "Path is blocked!", False

            if captured_pos is None:
                if self.multi_jump_active:
                    return False, "Must complete capture combo!", False
                self.board[er][ec] = p
                self.board[sr][sc] = EMPTY
                return True, "King moved.", False
            else:
                cr, cc = captured_pos
                self.board[cr][cc] = EMPTY # Immediate removal
                self.board[er][ec] = p
                self.board[sr][sc] = EMPTY
                
                next_captures = self.get_all_legal_captures_for_piece(self.board, er, ec)
                if len(next_captures) > 0:
                    return True, "King captured! You can jump again.", True
                return True, "King capture complete.", False

        return False, "Invalid move!", False

    def _check_king(self, r, c):
        if self.board[r][c] == WHITE and r == 0:
            self.board[r][c] = WHITE_KING
        elif self.board[r][c] == BLACK and r == 7:
            self.board[r][c] = BLACK_KING


def render_board_image(game: DamaGame):
    cell_size = 120
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

            # Highlight selected piece (Green)
            if game.selected_from and game.selected_from == (r, c):
                draw.rectangle([x1+4, y1+4, x2-4, y2-4], outline="#2ECC71", width=8)

            # Player 1 Cursor (Cyan)
            if game.cursor_p1 == [r, c]:
                draw.rectangle([x1+8, y1+8, x2-8, y2-8], outline="#00FFFF", width=6)

            # Player 2 Cursor (Orange)
            if game.cursor_p2 == [r, c]:
                draw.rectangle([x1+12, y1+12, x2-12, y2-12], outline="#FF9900", width=6)

            piece = game.board[r][c]
            if piece != EMPTY:
                px1, py1 = x1 + 14, y1 + 14
                px2, py2 = x2 - 14, y2 - 14
                pcolor = "#FFFFFF" if piece in (WHITE, WHITE_KING) else "#E74C3C"
                draw.ellipse([px1, py1, px2, py2], fill=pcolor, outline="#000000", width=4)
                
                # DRAW GOLDEN CROWN LOGO FOR KING PIECES 👑
                if piece in (WHITE_KING, BLACK_KING):
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    crown_color = "#F1C40F"
                    # Crown points geometry
                    crown_pts = [
                        (cx - 25, cy + 15),
                        (cx - 30, cy - 15),
                        (cx - 12, cy - 2),
                        (cx, cy - 22),
                        (cx + 12, cy - 2),
                        (cx + 30, cy - 15),
                        (cx + 25, cy + 15)
                    ]
                    draw.polygon(crown_pts, fill=crown_color, outline="#000000")
                    draw.ellipse([cx - 22, cy + 10, cx + 22, cy + 20], fill="#D4AC0D")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


class DPadView(View):
    def __init__(self, game: DamaGame):
        super().__init__(timeout=None)
        self.game = game
        self.step_size = 1  # Standard step movement

    async def update_board_message(self, interaction: discord.Interaction, notice: str = ""):
        image_bytes = render_board_image(self.game)
        file = discord.File(fp=image_bytes, filename="dama_board.png")
        sel_text = f"\n📌 **Selected Piece:** Row {self.game.selected_from[0]}, Col {self.game.selected_from[1]}" if self.game.selected_from else ""
        cur = self.game.current_cursor
        content = f"**Current Turn:** {self.game.turn.mention}{sel_text}\n📍 **Your Cursor:** Row {cur[0]}, Col {cur[1]} *(Speed: {self.step_size}x)* {notice}"
        await interaction.response.edit_message(content=content, attachments=[file], view=self)

    async def move_cursor(self, interaction: discord.Interaction, dr: int, dc: int):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        cur = self.game.current_cursor
        cur[0] = max(0, min(7, cur[0] + (dr * self.step_size)))
        cur[1] = max(0, min(7, cur[1] + (dc * self.step_size)))
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

    @discord.ui.button(label="⚡ Speed: 1x", style=discord.ButtonStyle.secondary, row=0)
    async def speed_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        # Cycle speed between 1x -> 3x -> 5x
        if self.step_size == 1:
            self.step_size = 3
            button.label = "🚀 Speed: 3x"
        elif self.step_size == 3:
            self.step_size = 5
            button.label = "🔥 Speed: 5x"
        else:
            self.step_size = 1
            button.label = "⚡ Speed: 1x"
        await self.update_board_message(interaction)

    @discord.ui.button(label="🎯 Select Piece", style=discord.ButtonStyle.secondary, row=3)
    async def select_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        if self.game.multi_jump_active:
            return await interaction.response.send_message("❌ You are mid-combo! Continue jumping with your active piece.", ephemeral=True)
        
        r, c = self.game.current_cursor
        color = WHITE if self.game.turn == self.game.p1 else BLACK
        p = self.game.board[r][c]
        if self.game.get_piece_color(p) != color:
            return await interaction.response.send_message("❌ Choose one of your own pieces!", ephemeral=True)
            
        self.game.selected_from = (r, c)
        await self.update_board_message(interaction, notice="\n✅ *Piece Selected! Move cursor to target square and tap Confirm Move.*")

    @discord.ui.button(label="✅ Confirm Move", style=discord.ButtonStyle.success, row=3)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.game.turn:
            return await interaction.response.send_message("It's not your turn!", ephemeral=True)
        if not self.game.selected_from:
            return await interaction.response.send_message("❌ Tap 'Select Piece' first!", ephemeral=True)

        sr, sc = self.game.selected_from
        er, ec = self.game.current_cursor
        success, msg, can_continue = self.game.move_piece(sr, sc, er, ec)

        if success:
            if can_continue:
                self.game.multi_jump_active = True
                self.game.selected_from = (er, ec)
                await self.update_board_message(interaction, notice=f"\n🔥 **MULTI-JUMP COMBO!** Tap direction & Confirm to execute next jump!")
            else:
                self.game.multi_jump_active = False
                self.game.selected_from = None
                self.game.turn = self.game.p2 if self.game.turn == self.game.p1 else self.game.p1
                await self.update_board_message(interaction)
        else:
            await interaction.response.send_message(f"❌ **Invalid Move:** {msg}", ephemeral=True)
