"""
Andy Dufresne in the rain - animated ASCII art
Run:  python andy_in_rain.py      (Ctrl+C to stop)
"""
import random
import sys
import time

WIDTH, HEIGHT = 60, 24
GROUND_Y = HEIGHT - 3
NUM_DROPS = 70
FPS = 20

# ANSI colours
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"
RESET = "\033[0m"

ANDY = [
    r" \         / ",
    r"  \       /  ",
    r"   \     /   ",
    r"    \ O /    ",
    r"     \|/     ",
    r"      |      ",
    r"      |      ",
    r"     / \     ",
    r"    /   \    ",
    r"   /     \   ",
]

CAPTION = "ANDY DUFRESNE  -  FREEDOM"


def make_drop():
    return [random.randint(0, WIDTH - 1), random.randint(-HEIGHT, 0), random.choice("|'.")]


def main():
    drops = [make_drop() for _ in range(NUM_DROPS)]
    splashes = []  # [x, life]

    andy_x = (WIDTH - len(ANDY[0])) // 2
    andy_y = GROUND_Y - len(ANDY)

    sys.stdout.write("\033[2J\033[?25l")  # clear screen, hide cursor
    try:
        while True:
            # blank canvas: each cell is (char, colour)
            grid = [[(" ", RESET) for _ in range(WIDTH)] for _ in range(HEIGHT)]

            # rain
            for d in drops:
                d[1] += 1
                if d[1] >= GROUND_Y:
                    splashes.append([d[0], 3])
                    d[0], d[1], d[2] = make_drop()[0], random.randint(-8, 0), random.choice("|'.")
                if 0 <= d[1] < GROUND_Y:
                    grid[d[1]][d[0]] = (d[2], BLUE)

            # ground and splashes
            for x in range(WIDTH):
                grid[GROUND_Y][x] = ("=", GRAY)
            for s in splashes:
                s[1] -= 1
            splashes[:] = [s for s in splashes if s[1] > 0]
            for x, life in splashes:
                ch = "o" if life == 2 else "."
                grid[GROUND_Y - 1][x] = (ch, CYAN)

            # Andy (drawn last so rain falls behind him)
            for row, line in enumerate(ANDY):
                for col, ch in enumerate(line):
                    if ch != " ":
                        grid[andy_y + row][andy_x + col] = (ch, WHITE)

            # caption
            cx = (WIDTH - len(CAPTION)) // 2
            for i, ch in enumerate(CAPTION):
                grid[HEIGHT - 1][cx + i] = (ch, WHITE)

            # render
            out = ["\033[H"]
            for row in grid:
                out.append("".join(c + ch for ch, c in row) + RESET + "\n")
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            time.sleep(1 / FPS)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h" + RESET + "\n")  # show cursor again


if __name__ == "__main__":
    main()