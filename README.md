# Falling Blocks Puzzle Game

A Tetris-style falling blocks game built with Python and Pygame. Features four game modes, an AI auto-play system, procedurally generated audio, and a local high score tracker.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Pygame](https://img.shields.io/badge/Pygame-2.x-green)

## Features

- **4 Game Modes** — Classic, Challenge, AI Auto-Play, and Local Multiplayer
- **AI Auto-Play** — heuristic-based AI that evaluates height, holes, and bumpiness
- **Challenge Mode** — garbage rows rise from the bottom over time
- **Local Multiplayer** — two players alternate turns on the same keyboard
- **Ghost Piece** — shows where the current piece will land
- **Combo System** — bonus points for consecutive line clears
- **Procedural Audio** — all sounds generated in-code, no external audio files needed
- **High Score Saving** — per-mode high scores saved locally to `high_score.json`

## Requirements

- Python 3.8+
- Pygame 2.x

## Installation

```bash
git clone https://github.com/199993hui/Tetris.git
cd Tetris
pip install pygame
python falling_blocks_pygame.py
```

## Controls

### Menu
| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate modes |
| `Enter` / `Space` | Start selected mode |
| `1` – `4` | Start mode directly |
| `M` | Toggle audio |
| `ESC` | Quit |

### During Game
| Key | Action |
|-----|--------|
| `←` / `→` | Move piece |
| `↓` | Soft drop |
| `↑` / `X` | Rotate clockwise |
| `Space` | Hard drop |
| `P` | Pause / Resume |
| `M` | Toggle audio |
| `ESC` | Return to menu |

### Game Over
| Key | Action |
|-----|--------|
| `R` | Restart same mode |
| `Enter` | Return to menu |

## Scoring

| Lines Cleared | Base Points |
|---------------|-------------|
| 1 | 100 |
| 2 | 300 |
| 3 | 500 |
| 4 (Tetris) | 800 |

Combo bonuses, level multipliers, and hard drop distance also add to your score.

## Project Structure

```
Tetris/
├── falling_blocks_pygame.py   # Main game file
├── high_score.json            # Auto-generated, saved locally (git-ignored)
├── .gitignore
└── README.md
```
