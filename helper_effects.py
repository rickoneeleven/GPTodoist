import os
import random
import shutil
import sys
import time
from typing import Tuple



def _term_size() -> Tuple[int, int]:
    size = shutil.get_terminal_size((80, 24))
    return max(40, size.columns), max(12, size.lines)


def _ansi_supported() -> bool:
    if not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    return term and term.lower() != "dumb"


def _hide_cursor() -> None:
    sys.stdout.write("\x1b[?25l")


def _show_cursor() -> None:
    sys.stdout.write("\x1b[?25h")


def _clear_screen() -> None:
    sys.stdout.write("\x1b[2J\x1b[H")


def _center_print(row: int, text: str, width: int, color: str = "") -> None:
    col = max(1, (width - len(text)) // 2 + 1)
    if color:
        sys.stdout.write(f"\x1b[{row};{col}H{color}{text}\x1b[0m")
    else:
        sys.stdout.write(f"\x1b[{row};{col}H{text}")


def _animate_confetti(duration: float = 1.8) -> None:
    width, height = _term_size()
    frame_time = 0.06
    frames = max(10, int(duration / frame_time))
    palette = [196, 202, 208, 214, 220, 190, 82, 51, 45, 99, 93, 201]
    chars = ["*", ".", "+", "o", "O", "@", "$"]

    try:
        _hide_cursor()
        start = time.time()
        for i in range(frames):
            _clear_screen()

            # headline
            headline = "ALL TASKS DONE!"
            sub = "Great job - enjoy the win"
            row_h = max(2, height // 2 - 2)
            row_s = row_h + 2
            _center_print(row_h, headline, width, "\x1b[1;38;5;46m")
            _center_print(row_s, sub, width, "\x1b[2;38;5;39m")

            # burst from the center
            cx = width // 2
            cy = height // 2
            particles = min(250, (width * height) // 18)
            spread = 1 + i * 0.6
            for _ in range(particles):
                angle = random.random() * 6.28318
                radius = random.random() * spread
                x = int(cx + radius * 2.0 * (1.0 + 0.4 * random.random()) * (1 if random.random() < 0.5 else -1) * 0.5 * (1 + random.random()))
                y = int(cy + radius * (1 if random.random() < 0.5 else -1))
                if 1 <= y <= height and 1 <= x <= width:
                    color = random.choice(palette)
                    ch = random.choice(chars)
                    sys.stdout.write(f"\x1b[{y};{x}H\x1b[38;5;{color}m{ch}\x1b[0m")

            # soft bottom confetti line
            row_b = height - 2
            for _ in range(width // 2):
                x = random.randint(1, width)
                color = random.choice(palette)
                ch = random.choice(chars)
                sys.stdout.write(f"\x1b[{row_b};{x}H\x1b[38;5;{color}m{ch}\x1b[0m")

            sys.stdout.flush()

            elapsed = time.time() - start
            remaining = (i + 1) * frame_time - elapsed
            if remaining > 0:
                time.sleep(remaining)
    finally:
        _show_cursor()


def _static_fireworks(duration: float = 1.8) -> None:
    width, height = _term_size()
    _clear_screen()
    art = [
        "            .''.       .''.            ",
        "        .''.      .        *''.        ",
        "       *'   *   *'   *        '*       ",
        "        ' *   *  *  *    *    *        ",
        "             '*._.*'   '*._.*'         ",
    ]
    row = max(2, height // 2 - 4)
    for i, line in enumerate(art):
        color = 196 + (i * 3) % 30
        _center_print(row + i, line, width, f"\x1b[38;5;{color}m")
    _center_print(row + len(art) + 1, "ALL TASKS DONE!", width, "\x1b[1;38;5;46m")
    _center_print(row + len(art) + 3, "Great job - enjoy the win", width, "\x1b[2;38;5;39m")
    sys.stdout.flush()
    # Hold the static celebration for the requested duration
    time.sleep(max(0.2, duration))


def play_completion_celebration(duration: float = 1.8) -> None:
    try:
        if _ansi_supported():
            _animate_confetti(duration)
        else:
            _static_fireworks(duration)
    finally:
        pass
