"""
Falling-Blocks Puzzle Game using Pygame

Required features:
    - 10 x 20 game grid
    - 7 tetromino shapes
    - Movement, rotation, soft drop, and hard drop
    - Collision detection
    - Line clearing
    - Score and combo system
    - Game over condition
    - Pygame rendering at 60 FPS

Audio feature:
    - Background music tone
    - Sound effects for movement, rotation, landing, line clear, garbage row,
      game over, and new high score
    - M key toggles mute/unmute

Advanced features included:
    1. High-score saving using high_score.json
    2. AI Auto-Play mode
    3. Custom Challenge mode with rising garbage rows
    4. Local Multiplayer alternating turns

Controls:
    Menu:
        1       Classic Mode
        2       Challenge Mode
        3       AI Auto-Play Mode
        4       Local Multiplayer Mode
        M       Mute / unmute audio
        ESC     Quit

    During game:
        LEFT / RIGHT  Move piece horizontally
        DOWN          Soft drop
        UP or X       Rotate clockwise
        SPACE         Hard drop
        P             Pause / resume
        M             Mute / unmute audio
        ESC           Return to menu

    Game over:
        R             Restart same mode
        ENTER         Return to menu
        ESC           Return to menu

"""

import json
import math
import os
import random
import sys
from array import array
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame


# -----------------------------
# Game configuration
# -----------------------------
COLS = 10
ROWS = 20
BLOCK_SIZE = 30
SIDE_PANEL = 250
TOP_MARGIN = 30
SCREEN_WIDTH = COLS * BLOCK_SIZE + SIDE_PANEL
SCREEN_HEIGHT = ROWS * BLOCK_SIZE + TOP_MARGIN * 2

FPS = 60
NORMAL_FALL_MS = 650
SOFT_DROP_MS = 60
AI_MOVE_MS = 90
CHALLENGE_GARBAGE_MS = 24000
HIGH_SCORE_FILE = "high_score.json"

BG_COLOR = (18, 18, 28)
GRID_COLOR = (45, 45, 60)
EMPTY_CELL_COLOR = (28, 28, 40)
TEXT_COLOR = (240, 240, 245)
MUTED_TEXT = (185, 185, 200)
PANEL_COLOR = (25, 25, 38)
CARD_COLOR = (35, 35, 52)
GOLD = (255, 210, 70)
GREEN = (95, 230, 120)
RED = (255, 90, 95)
BLUE = (90, 160, 255)
PURPLE = (190, 100, 255)
ORANGE = (255, 165, 70)

SHAPES = {
    "I": [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    "O": [[0, 1, 1, 0], [0, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    "T": [[0, 1, 0, 0], [1, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    "S": [[0, 1, 1, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    "Z": [[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    "J": [[1, 0, 0, 0], [1, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    "L": [[0, 0, 1, 0], [1, 1, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
}

COLORS = {
    "I": (80, 220, 255),
    "O": (255, 220, 75),
    "T": (190, 100, 255),
    "S": (95, 230, 120),
    "Z": (255, 90, 95),
    "J": (90, 140, 255),
    "L": (255, 165, 70),
}

LINE_SCORE = {1: 100, 2: 300, 3: 500, 4: 800}
MODE_COLORS = {"Classic": BLUE, "Challenge": RED, "AI Auto": PURPLE, "Multiplayer": ORANGE}


# -----------------------------
# Helper functions
# -----------------------------
def rotate_matrix_clockwise(matrix: List[List[int]]) -> List[List[int]]:
    return [list(row) for row in zip(*matrix[::-1])]


def trim_matrix(matrix: List[List[int]]) -> List[List[int]]:
    """Remove empty outside rows and columns so AI can compare piece widths."""
    cells = [(x, y) for y, row in enumerate(matrix) for x, value in enumerate(row) if value]
    if not cells:
        return matrix
    min_x = min(x for x, _ in cells)
    max_x = max(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    max_y = max(y for _, y in cells)
    return [row[min_x : max_x + 1] for row in matrix[min_y : max_y + 1]]


def draw_text(surface, text, font, color, x, y, center=False):
    image = font.render(str(text), True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(image, rect)
    return rect


def draw_rounded_box(surface, rect, color, border_color=None, border_width=0, radius=18):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color and border_width > 0:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)


# -----------------------------
# Audio manager
# -----------------------------
class AudioManager:
    """Creates and plays simple generated sounds without external files."""

    def __init__(self):
        self.enabled = True
        self.ready = False
        self.sounds = {}
        self.music_channel: Optional[pygame.mixer.Channel] = None
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
            pygame.mixer.init()
            self.ready = True
            self.create_sounds()
            self.start_background_music()
        except pygame.error:
            self.ready = False

    def make_tone(self, frequency: int, duration_ms: int, volume: float = 0.35) -> pygame.mixer.Sound:
        sample_rate = 44100
        sample_count = int(sample_rate * duration_ms / 1000)
        amplitude = int(32767 * volume)
        samples = array("h")
        fade_samples = max(1, int(sample_rate * 0.015))
        for i in range(sample_count):
            t = i / sample_rate
            fade = 1.0
            if i < fade_samples:
                fade = i / fade_samples
            elif i > sample_count - fade_samples:
                fade = (sample_count - i) / fade_samples
            samples.append(int(amplitude * fade * math.sin(2 * math.pi * frequency * t)))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def make_background_loop(self) -> pygame.mixer.Sound:
        sample_rate = 44100
        duration_ms = 1800
        sample_count = int(sample_rate * duration_ms / 1000)
        notes = [196, 247, 294, 247]
        samples = array("h")
        amplitude = int(32767 * 0.10)
        for i in range(sample_count):
            t = i / sample_rate
            frequency = notes[min(int((i / sample_count) * len(notes)), len(notes) - 1)]
            wave = math.sin(2 * math.pi * frequency * t)
            wave += 0.45 * math.sin(2 * math.pi * frequency * 2 * t)
            samples.append(int(amplitude * wave))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def create_sounds(self):
        self.sounds = {
            "move": self.make_tone(440, 45, 0.16),
            "rotate": self.make_tone(620, 70, 0.20),
            "drop": self.make_tone(180, 90, 0.25),
            "land": self.make_tone(120, 100, 0.28),
            "line": self.make_tone(760, 160, 0.34),
            "garbage": self.make_tone(100, 240, 0.32),
            "game_over": self.make_tone(90, 500, 0.35),
            "new_high": self.make_tone(880, 420, 0.34),
            "select": self.make_tone(520, 80, 0.22),
            "music": self.make_background_loop(),
        }

    def start_background_music(self):
        if not self.ready:
            return
        self.music_channel = pygame.mixer.Channel(0)
        self.music_channel.set_volume(0.22)
        self.music_channel.play(self.sounds["music"], loops=-1)

    def play(self, name: str):
        if not self.ready or not self.enabled:
            return
        if name in self.sounds:
            self.sounds[name].play()

    def toggle_mute(self):
        if not self.ready:
            return
        self.enabled = not self.enabled
        if self.enabled:
            pygame.mixer.unpause()
            if self.music_channel and not self.music_channel.get_busy():
                self.start_background_music()
        else:
            pygame.mixer.pause()

    def pause_music(self):
        if self.ready and self.enabled:
            pygame.mixer.pause()

    def resume_music(self):
        if self.ready and self.enabled:
            pygame.mixer.unpause()


# -----------------------------
# High-score manager
# -----------------------------
class HighScoreManager:
    """Loads and saves one high score for each game mode."""

    def __init__(self, filename: str):
        self.filename = filename
        self.scores = self.load_scores()

    def load_scores(self) -> Dict[str, int]:
        default_scores = {"Classic": 0, "Challenge": 0, "AI Auto": 0, "Multiplayer": 0}
        if not os.path.exists(self.filename):
            return default_scores
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                data = json.load(file)
            if "high_score" in data:
                default_scores["Classic"] = int(data.get("high_score", 0))
            if "scores" in data:
                for mode, score in data["scores"].items():
                    if mode in default_scores:
                        default_scores[mode] = int(score)
            return default_scores
        except (OSError, ValueError, json.JSONDecodeError):
            return default_scores

    def get_high_score(self, mode: str) -> int:
        return int(self.scores.get(mode, 0))

    def save_high_score(self, mode: str, score: int):
        if score <= self.get_high_score(mode):
            return
        self.scores[mode] = score
        try:
            with open(self.filename, "w", encoding="utf-8") as file:
                json.dump({"scores": self.scores}, file, indent=4)
        except OSError:
            pass


# -----------------------------
# Piece class
# -----------------------------
@dataclass
class Piece:
    shape_name: str
    matrix: List[List[int]]
    color: Tuple[int, int, int]
    x: int = 3
    y: int = 0

    @classmethod
    def random_piece(cls):
        name = random.choice(list(SHAPES.keys()))
        return cls(name, [row[:] for row in SHAPES[name]], COLORS[name])

    def copy(self):
        return Piece(self.shape_name, [row[:] for row in self.matrix], self.color, self.x, self.y)

    def cells(self, matrix=None, offset_x=0, offset_y=0) -> List[Tuple[int, int]]:
        if matrix is None:
            matrix = self.matrix
        occupied = []
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                if value:
                    occupied.append((self.x + col_index + offset_x, self.y + row_index + offset_y))
        return occupied

    def rotated_matrix(self) -> List[List[int]]:
        return rotate_matrix_clockwise(self.matrix)


# -----------------------------
# Main game class
# -----------------------------
class FallingBlocksGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Falling Blocks Puzzle Game")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.audio = AudioManager()
        self.high_scores = HighScoreManager(HIGH_SCORE_FILE)

        self.font_title = pygame.font.SysFont("consolas", 42, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 34, bold=True)
        self.font_medium = pygame.font.SysFont("consolas", 23, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 17)
        self.font_tiny = pygame.font.SysFont("consolas", 14)

        self.state = "menu"
        self.game_mode = "Classic"
        self.menu_options = ["Classic", "Challenge", "AI Auto", "Multiplayer"]
        self.menu_index = 0
        self.reset_game()

    # -----------------------------
    # Game state setup
    # -----------------------------
    def reset_game(self):
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.current_piece = Piece.random_piece()
        self.next_piece = Piece.random_piece()
        self.score = 0
        self.lines_cleared_total = 0
        self.combo = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.new_high_score = False
        self.last_fall_time = pygame.time.get_ticks()
        self.last_garbage_time = pygame.time.get_ticks()
        self.last_ai_time = pygame.time.get_ticks()
        self.ai_target = None

        self.current_player = 1
        self.player_scores = {1: 0, 2: 0}
        self.player_turn_pieces = 0
        self.turn_message_until = 0

    def start_mode(self, mode: str):
        self.game_mode = mode
        self.reset_game()
        self.state = "playing"
        self.audio.play("select")
        self.audio.resume_music()

    def return_to_menu(self):
        self.state = "menu"
        self.paused = False
        self.audio.resume_music()

    # -----------------------------
    # Collision and movement logic
    # -----------------------------
    def is_valid_position(self, piece: Piece, matrix=None, offset_x=0, offset_y=0) -> bool:
        for x, y in piece.cells(matrix=matrix, offset_x=offset_x, offset_y=offset_y):
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y < 0:
                continue
            if self.grid[y][x] is not None:
                return False
        return True

    def move_piece(self, dx: int, dy: int, play_sound: bool = False) -> bool:
        if self.is_valid_position(self.current_piece, offset_x=dx, offset_y=dy):
            self.current_piece.x += dx
            self.current_piece.y += dy
            if play_sound and dx != 0:
                self.audio.play("move")
            return True
        return False

    def rotate_piece(self, play_sound: bool = True) -> bool:
        rotated = self.current_piece.rotated_matrix()
        for kick_x in [0, -1, 1, -2, 2]:
            if self.is_valid_position(self.current_piece, matrix=rotated, offset_x=kick_x):
                self.current_piece.matrix = rotated
                self.current_piece.x += kick_x
                if play_sound:
                    self.audio.play("rotate")
                return True
        return False

    def hard_drop(self):
        distance = 0
        while self.move_piece(0, 1):
            distance += 1
        self.score += distance * 2
        if self.game_mode == "Multiplayer":
            self.player_scores[self.current_player] += distance * 2
        self.audio.play("drop")
        self.lock_piece()

    # -----------------------------
    # Grid and scoring logic
    # -----------------------------
    def lock_piece(self):
        for x, y in self.current_piece.cells():
            if y < 0:
                self.end_game()
                return
            if 0 <= y < ROWS and 0 <= x < COLS:
                self.grid[y][x] = self.current_piece.color

        self.audio.play("land")
        cleared = self.clear_completed_lines()
        self.update_score(cleared)
        self.after_piece_locked()
        self.spawn_next_piece()

    def clear_completed_lines(self) -> int:
        new_grid = []
        cleared = 0
        for row in self.grid:
            if all(cell is not None for cell in row):
                cleared += 1
            else:
                new_grid.append(row)
        for _ in range(cleared):
            new_grid.insert(0, [None for _ in range(COLS)])
        self.grid = new_grid
        return cleared

    def update_score(self, cleared: int):
        if cleared > 0:
            self.combo += 1
            base_score = LINE_SCORE.get(cleared, 0)
            combo_bonus = (self.combo - 1) * 50
            level_bonus = self.level * 10
            mode_bonus = 50 if self.game_mode == "Challenge" else 0
            gained = base_score + combo_bonus + level_bonus + mode_bonus
            self.score += gained
            if self.game_mode == "Multiplayer":
                self.player_scores[self.current_player] += gained
            self.lines_cleared_total += cleared
            self.level = 1 + self.lines_cleared_total // 10
            self.audio.play("line")
        else:
            self.combo = 0

    def after_piece_locked(self):
        if self.game_mode != "Multiplayer":
            return
        self.player_turn_pieces += 1
        if self.player_turn_pieces >= 2:
            self.current_player = 2 if self.current_player == 1 else 1
            self.player_turn_pieces = 0
            self.turn_message_until = pygame.time.get_ticks() + 1200

    def spawn_next_piece(self):
        self.current_piece = self.next_piece
        self.current_piece.x = 3
        self.current_piece.y = 0
        self.next_piece = Piece.random_piece()
        self.ai_target = None
        if not self.is_valid_position(self.current_piece):
            self.end_game()

    def add_garbage_row(self):
        if self.game_mode != "Challenge" or self.game_over or self.paused:
            return
        if any(cell is not None for cell in self.grid[0]):
            self.end_game()
            return
        hole = random.randint(0, COLS - 1)
        garbage_row = [(95, 95, 115) if x != hole else None for x in range(COLS)]
        self.grid.pop(0)
        self.grid.append(garbage_row)
        self.current_piece.y -= 1
        if not self.is_valid_position(self.current_piece):
            self.end_game()
            return
        self.audio.play("garbage")

    def end_game(self):
        if self.game_over:
            return
        self.game_over = True
        self.state = "game_over"
        self.audio.play("game_over")
        old_high = self.high_scores.get_high_score(self.game_mode)
        self.new_high_score = self.score > old_high
        self.high_scores.save_high_score(self.game_mode, self.score)
        if self.new_high_score:
            self.audio.play("new_high")

    # -----------------------------
    # AI Auto-Play advanced feature
    # -----------------------------
    def simulate_drop_score(self, test_piece: Piece) -> Tuple[float, int]:
        """Give a score to a simulated final position for AI decision-making."""
        while self.is_valid_position(test_piece, offset_y=1):
            test_piece.y += 1

        test_grid = [row[:] for row in self.grid]
        for x, y in test_piece.cells():
            if 0 <= y < ROWS and 0 <= x < COLS:
                test_grid[y][x] = test_piece.color

        lines = sum(1 for row in test_grid if all(cell is not None for cell in row))
        heights = []
        holes = 0
        for x in range(COLS):
            first_block = None
            for y in range(ROWS):
                if test_grid[y][x] is not None:
                    first_block = y
                    break
            if first_block is None:
                heights.append(0)
            else:
                heights.append(ROWS - first_block)
                for y in range(first_block + 1, ROWS):
                    if test_grid[y][x] is None:
                        holes += 1

        bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
        total_height = sum(heights)
        score = lines * 1000 - holes * 90 - total_height * 8 - bumpiness * 12
        return score, test_piece.x

    def choose_ai_target(self):
        """Choose the best rotation and x-position for the current piece."""
        best_score = -10**9
        best_matrix = self.current_piece.matrix
        best_x = self.current_piece.x
        seen_rotations = set()
        matrix = [row[:] for row in self.current_piece.matrix]

        for _ in range(4):
            trimmed_key = tuple(tuple(row) for row in trim_matrix(matrix))
            if trimmed_key not in seen_rotations:
                seen_rotations.add(trimmed_key)
                for x in range(-2, COLS + 2):
                    test_piece = Piece(self.current_piece.shape_name, [row[:] for row in matrix], self.current_piece.color, x, self.current_piece.y)
                    if self.is_valid_position(test_piece):
                        score, final_x = self.simulate_drop_score(test_piece)
                        if score > best_score:
                            best_score = score
                            best_matrix = [row[:] for row in matrix]
                            best_x = final_x
            matrix = rotate_matrix_clockwise(matrix)

        self.ai_target = {"matrix": best_matrix, "x": best_x}

    def update_ai(self):
        if self.game_mode != "AI Auto" or self.game_over or self.paused:
            return
        now = pygame.time.get_ticks()
        if now - self.last_ai_time < AI_MOVE_MS:
            return
        self.last_ai_time = now

        if self.ai_target is None:
            self.choose_ai_target()

        if self.ai_target is None:
            return

        if self.current_piece.matrix != self.ai_target["matrix"]:
            self.rotate_piece(play_sound=False)
            return

        target_x = self.ai_target["x"]
        if self.current_piece.x < target_x:
            self.move_piece(1, 0)
        elif self.current_piece.x > target_x:
            self.move_piece(-1, 0)
        else:
            self.move_piece(0, 1)

    # -----------------------------
    # Time and input handling
    # -----------------------------
    def current_fall_delay(self) -> int:
        mode_penalty = 120 if self.game_mode == "Challenge" else 0
        return max(95, NORMAL_FALL_MS - mode_penalty - (self.level - 1) * 45)

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.audio.pause_music()
        else:
            self.audio.resume_music()
            self.last_fall_time = pygame.time.get_ticks()
            self.last_garbage_time = pygame.time.get_ticks()

    def handle_menu_key(self, event):
        if event.key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
            self.audio.play("move")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)
            self.audio.play("move")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.start_mode(self.menu_options[self.menu_index])
        elif event.key == pygame.K_1:
            self.start_mode("Classic")
        elif event.key == pygame.K_2:
            self.start_mode("Challenge")
        elif event.key == pygame.K_3:
            self.start_mode("AI Auto")
        elif event.key == pygame.K_4:
            self.start_mode("Multiplayer")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in ("playing", "game_over"):
                        self.return_to_menu()
                    else:
                        self.quit_game()

                if event.key == pygame.K_m:
                    self.audio.toggle_mute()

                if self.state == "menu":
                    self.handle_menu_key(event)
                    continue

                if self.state == "game_over":
                    if event.key == pygame.K_r:
                        self.start_mode(self.game_mode)
                    elif event.key == pygame.K_RETURN:
                        self.return_to_menu()
                    continue

                if self.state != "playing":
                    continue

                if event.key == pygame.K_p:
                    self.toggle_pause()
                    continue

                if self.paused:
                    continue

                # AI Auto mode is controlled by the computer. Manual controls are disabled.
                if self.game_mode == "AI Auto":
                    continue

                if event.key == pygame.K_LEFT:
                    self.move_piece(-1, 0, play_sound=True)
                elif event.key == pygame.K_RIGHT:
                    self.move_piece(1, 0, play_sound=True)
                elif event.key in (pygame.K_UP, pygame.K_x):
                    self.rotate_piece()
                elif event.key == pygame.K_SPACE:
                    self.hard_drop()

        if self.state == "playing" and not self.game_over and not self.paused and self.game_mode != "AI Auto":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                now = pygame.time.get_ticks()
                if now - self.last_fall_time > SOFT_DROP_MS:
                    if not self.move_piece(0, 1):
                        self.lock_piece()
                    else:
                        self.score += 1
                        if self.game_mode == "Multiplayer":
                            self.player_scores[self.current_player] += 1
                    self.last_fall_time = now

    def update(self):
        if self.state != "playing" or self.game_over or self.paused:
            return

        self.update_ai()

        now = pygame.time.get_ticks()
        if now - self.last_fall_time > self.current_fall_delay():
            if not self.move_piece(0, 1):
                self.lock_piece()
            self.last_fall_time = now

        if self.game_mode == "Challenge" and now - self.last_garbage_time > CHALLENGE_GARBAGE_MS:
            self.add_garbage_row()
            self.last_garbage_time = now

    # -----------------------------
    # Drawing functions
    # -----------------------------
    def draw_cell(self, x: int, y: int, color):
        pixel_x = x * BLOCK_SIZE
        pixel_y = TOP_MARGIN + y * BLOCK_SIZE
        rect = pygame.Rect(pixel_x, pixel_y, BLOCK_SIZE, BLOCK_SIZE)
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, (10, 10, 15), rect, 2)
        highlight = pygame.Rect(pixel_x + 4, pixel_y + 4, BLOCK_SIZE - 8, 5)
        pygame.draw.rect(self.screen, tuple(min(c + 35, 255) for c in color), highlight)

    def draw_grid_background(self):
        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(x * BLOCK_SIZE, TOP_MARGIN + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(self.screen, EMPTY_CELL_COLOR, rect)
                pygame.draw.rect(self.screen, GRID_COLOR, rect, 1)

    def draw_locked_blocks(self):
        for y, row in enumerate(self.grid):
            for x, color in enumerate(row):
                if color is not None:
                    self.draw_cell(x, y, color)

    def draw_current_piece(self):
        for x, y in self.current_piece.cells():
            if y >= 0:
                self.draw_cell(x, y, self.current_piece.color)

    def get_ghost_y(self) -> int:
        ghost_y = self.current_piece.y
        while self.is_valid_position(self.current_piece, offset_y=(ghost_y - self.current_piece.y) + 1):
            ghost_y += 1
        return ghost_y

    def draw_ghost_piece(self):
        ghost_y = self.get_ghost_y()
        offset = ghost_y - self.current_piece.y
        ghost_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for x, y in self.current_piece.cells(offset_y=offset):
            if y >= 0:
                rect = pygame.Rect(x * BLOCK_SIZE, TOP_MARGIN + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(ghost_surface, (*self.current_piece.color, 70), rect)
                pygame.draw.rect(ghost_surface, (*TEXT_COLOR, 100), rect, 2)
        self.screen.blit(ghost_surface, (0, 0))

    def draw_next_piece(self, start_x: int, start_y: int):
        for row_index, row in enumerate(self.next_piece.matrix):
            for col_index, value in enumerate(row):
                if value:
                    rect = pygame.Rect(start_x + col_index * BLOCK_SIZE, start_y + row_index * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                    pygame.draw.rect(self.screen, self.next_piece.color, rect)
                    pygame.draw.rect(self.screen, (10, 10, 15), rect, 2)

    def draw_side_panel(self):
        panel_x = COLS * BLOCK_SIZE
        pygame.draw.rect(self.screen, PANEL_COLOR, (panel_x, 0, SIDE_PANEL, SCREEN_HEIGHT))

        draw_text(self.screen, "FALLING", self.font_medium, TEXT_COLOR, panel_x + SIDE_PANEL // 2, 30, center=True)
        draw_text(self.screen, "BLOCKS", self.font_medium, TEXT_COLOR, panel_x + SIDE_PANEL // 2, 60, center=True)

        mode_color = MODE_COLORS.get(self.game_mode, BLUE)
        mode_rect = pygame.Rect(panel_x + 24, 98, SIDE_PANEL - 48, 36)
        draw_rounded_box(self.screen, mode_rect, CARD_COLOR, mode_color, 2, 12)
        draw_text(self.screen, self.game_mode.upper(), self.font_small, mode_color, mode_rect.centerx, mode_rect.centery, center=True)

        y = 150
        draw_text(self.screen, "Score", self.font_small, MUTED_TEXT, panel_x + 24, y)
        draw_text(self.screen, str(self.score), self.font_medium, GOLD, panel_x + 24, y + 22)

        y += 62
        draw_text(self.screen, "High Score", self.font_small, MUTED_TEXT, panel_x + 24, y)
        draw_text(self.screen, str(self.high_scores.get_high_score(self.game_mode)), self.font_medium, GREEN, panel_x + 24, y + 22)

        y += 68
        draw_text(self.screen, f"Lines: {self.lines_cleared_total}", self.font_small, TEXT_COLOR, panel_x + 24, y)
        draw_text(self.screen, f"Level: {self.level}", self.font_small, TEXT_COLOR, panel_x + 24, y + 22)
        draw_text(self.screen, f"Combo: {self.combo}", self.font_small, TEXT_COLOR, panel_x + 24, y + 44)
        audio_status = "On" if self.audio.enabled and self.audio.ready else "Off"
        draw_text(self.screen, f"Audio: {audio_status}", self.font_small, TEXT_COLOR, panel_x + 24, y + 66)

        if self.game_mode == "Challenge" and self.state == "playing":
            elapsed = pygame.time.get_ticks() - self.last_garbage_time
            seconds_left = max(0, (CHALLENGE_GARBAGE_MS - elapsed) // 1000)
            draw_text(self.screen, f"Garbage: {seconds_left}s", self.font_small, RED, panel_x + 24, y + 88)

        if self.game_mode == "Multiplayer":
            mp_y = y + 96
            draw_text(self.screen, f"P1: {self.player_scores[1]}", self.font_small, BLUE if self.current_player == 1 else MUTED_TEXT, panel_x + 24, mp_y)
            draw_text(self.screen, f"P2: {self.player_scores[2]}", self.font_small, ORANGE if self.current_player == 2 else MUTED_TEXT, panel_x + 120, mp_y)
            draw_text(self.screen, f"Turn: Player {self.current_player}", self.font_small, GOLD, panel_x + 24, mp_y + 22)

        y = 415
        draw_text(self.screen, "Next", self.font_medium, TEXT_COLOR, panel_x + 24, y)
        self.draw_next_piece(panel_x + 36, y + 40)

        y = 535
        draw_text(self.screen, "Controls", self.font_small, MUTED_TEXT, panel_x + 24, y)
        controls = ["Arrows: Move/Drop", "Up/X: Rotate", "Space: Hard drop", "P: Pause", "M: Mute", "Esc: Menu"]
        if self.game_mode == "AI Auto":
            controls = ["AI controls piece", "P: Pause", "M: Mute", "Esc: Menu"]
        for i, line in enumerate(controls):
            draw_text(self.screen, line, self.font_tiny, TEXT_COLOR, panel_x + 24, y + 22 + i * 18)

    def draw_menu(self):
        self.screen.fill(BG_COLOR)
        cx = SCREEN_WIDTH // 2
        draw_text(self.screen, "FALLING BLOCKS", self.font_title, TEXT_COLOR, cx, 60, center=True)
        draw_text(self.screen, "Choose a game mode", self.font_small, MUTED_TEXT, cx, 105, center=True)

        descriptions = {
            "Classic": "Standard falling-block puzzle game.",
            "Challenge": "Custom mode: garbage rows rise over time.",
            "AI Auto": "Computer plays automatically using a simple AI.",
            "Multiplayer": "Two players alternate turns locally.",
        }

        start_y = 155
        card_w = 430
        card_h = 70
        for i, mode in enumerate(self.menu_options):
            y = start_y + i * 85
            rect = pygame.Rect(cx - card_w // 2, y, card_w, card_h)
            selected = i == self.menu_index
            color = MODE_COLORS[mode]
            fill = (42, 42, 62) if selected else CARD_COLOR
            border = color if selected else (65, 65, 82)
            draw_rounded_box(self.screen, rect, fill, border, 3 if selected else 1, 16)
            draw_text(self.screen, f"{i + 1}. {mode}", self.font_medium, color, rect.left + 24, rect.top + 13)
            draw_text(self.screen, descriptions[mode], self.font_tiny, MUTED_TEXT, rect.left + 24, rect.top + 42)

        draw_text(self.screen, "Use ↑/↓ then Enter, or press 1-4", self.font_small, TEXT_COLOR, cx, 520, center=True)
        audio_status = "ON" if self.audio.enabled and self.audio.ready else "OFF"
        draw_text(self.screen, f"M: Audio {audio_status}    ESC: Quit", self.font_tiny, MUTED_TEXT, cx, 550, center=True)

        hs_text = "High Scores: " + "   ".join(f"{m} {self.high_scores.get_high_score(m)}" for m in self.menu_options)
        draw_text(self.screen, hs_text, self.font_tiny, GOLD, cx, 585, center=True)

    def draw_new_high_score_overlay(self):
        overlay = pygame.Surface((COLS * BLOCK_SIZE, ROWS * BLOCK_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, TOP_MARGIN))

        board_w = COLS * BLOCK_SIZE
        box_rect = pygame.Rect(22, TOP_MARGIN + 142, board_w - 44, 300)
        shadow_rect = box_rect.move(0, 8)
        draw_rounded_box(self.screen, shadow_rect, (0, 0, 0), None, 0, 24)
        draw_rounded_box(self.screen, box_rect, CARD_COLOR, GOLD, 4, 24)

        cx = board_w // 2
        top = box_rect.top
        trophy_y = top + 30
        pygame.draw.circle(self.screen, GOLD, (cx, trophy_y + 28), 28)
        pygame.draw.rect(self.screen, GOLD, (cx - 12, trophy_y + 52, 24, 34), border_radius=8)
        pygame.draw.rect(self.screen, GOLD, (cx - 36, trophy_y + 84, 72, 10), border_radius=5)
        pygame.draw.arc(self.screen, GOLD, (cx - 72, trophy_y + 14, 55, 50), math.pi * 1.5, math.pi * 2.5, 5)
        pygame.draw.arc(self.screen, GOLD, (cx + 17, trophy_y + 14, 55, 50), math.pi * 0.5, math.pi * 1.5, 5)

        draw_text(self.screen, "NEW RECORD!", self.font_medium, GOLD, cx, top + 125, center=True)
        draw_text(self.screen, str(self.score), self.font_big, TEXT_COLOR, cx, top + 172, center=True)
        draw_text(self.screen, "points", self.font_small, MUTED_TEXT, cx, top + 205, center=True)
        draw_text(self.screen, f"Mode: {self.game_mode}", self.font_small, TEXT_COLOR, cx, top + 235, center=True)
        draw_text(self.screen, "R restart  |  Enter menu", self.font_tiny, MUTED_TEXT, cx, top + 268, center=True)

    def draw_game_over_overlay(self):
        if self.new_high_score:
            self.draw_new_high_score_overlay()
            return

        overlay = pygame.Surface((COLS * BLOCK_SIZE, ROWS * BLOCK_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, TOP_MARGIN))
        cx = COLS * BLOCK_SIZE // 2
        cy = TOP_MARGIN + ROWS * BLOCK_SIZE // 2
        card = pygame.Rect(30, cy - 95, COLS * BLOCK_SIZE - 60, 190)
        draw_rounded_box(self.screen, card, CARD_COLOR, RED, 3, 20)
        draw_text(self.screen, "GAME OVER", self.font_big, RED, cx, cy - 45, center=True)
        draw_text(self.screen, f"Final Score: {self.score}", self.font_small, TEXT_COLOR, cx, cy + 3, center=True)
        if self.game_mode == "Multiplayer":
            if self.player_scores[1] > self.player_scores[2]:
                winner = "Player 1 wins"
            elif self.player_scores[2] > self.player_scores[1]:
                winner = "Player 2 wins"
            else:
                winner = "Draw game"
            draw_text(self.screen, winner, self.font_small, GOLD, cx, cy + 28, center=True)
        draw_text(self.screen, "R restart  |  Enter menu", self.font_tiny, MUTED_TEXT, cx, cy + 62, center=True)

    def draw_pause_overlay(self):
        overlay = pygame.Surface((COLS * BLOCK_SIZE, ROWS * BLOCK_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, TOP_MARGIN))
        cx = COLS * BLOCK_SIZE // 2
        cy = TOP_MARGIN + ROWS * BLOCK_SIZE // 2
        draw_text(self.screen, "PAUSED", self.font_big, GOLD, cx, cy - 20, center=True)
        draw_text(self.screen, "Press P to continue", self.font_small, TEXT_COLOR, cx, cy + 25, center=True)

    def draw_turn_message(self):
        if self.game_mode != "Multiplayer" or pygame.time.get_ticks() > self.turn_message_until:
            return
        cx = COLS * BLOCK_SIZE // 2
        rect = pygame.Rect(55, TOP_MARGIN + 250, COLS * BLOCK_SIZE - 110, 72)
        draw_rounded_box(self.screen, rect, CARD_COLOR, GOLD, 3, 16)
        draw_text(self.screen, f"Player {self.current_player}'s Turn", self.font_medium, GOLD, cx, rect.centery, center=True)

    def draw_game(self):
        self.screen.fill(BG_COLOR)
        self.draw_grid_background()
        self.draw_locked_blocks()
        if not self.game_over:
            self.draw_ghost_piece()
            self.draw_current_piece()
        self.draw_side_panel()
        self.draw_turn_message()
        if self.paused:
            self.draw_pause_overlay()
        if self.state == "game_over":
            self.draw_game_over_overlay()

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()

    def quit_game(self):
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = FallingBlocksGame()
    game.run()
