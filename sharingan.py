"""
Sharingan (2 tomoe) -> 3 tomoe -> Mangekyou -> Rinnegan
Full-colour terminal animation (24-bit colour + half-block pixels).

Run in a real terminal (Windows Terminal / VS Code terminal / PowerShell):
    python sharingan.py
Ctrl+C to stop.  Terminal needs at least 56 columns x 22 rows.
"""
import math
import os
import sys
import time

FPS = 24
LOOP = True                      # blink and replay forever

# ---- eye geometry (all in "pixels"; one terminal cell = 1 wide x 2 tall pixels)
W_HALF, H_HALF = 26, 17          # half width / half height of the eye opening
IR = 13.0                        # iris radius
PUPIL = 2.5
RING_R = 9.4                     # thin black ring that holds the tomoe
ORBIT = 7.0                      # tomoe orbit radius
HEAD = 2.2                       # tomoe head radius
TAIL_ANGLE = 1.15                # tomoe tail length (radians)
MK_OUT = 11.0                    # mangekyou blade reach
RINGS = (4.3, 6.8, 9.2, 11.4)    # rinnegan ripple rings

GW = 2 * W_HALF + 3
GH = 36
CX = GW // 2
CY = (GH - 1) / 2

# ---- colours
BG = (10, 10, 14)
LID = (38, 22, 22)
SCLERA = (246, 240, 238)
SCLERA_EDGE = (196, 160, 158)
RED_IN, RED_OUT, LIMB_RED = (236, 28, 28), (150, 0, 8), (60, 0, 6)
PUR_IN, PUR_OUT, LIMB_PUR = (196, 176, 240), (140, 112, 200), (74, 52, 120)
RING_COL = (82, 56, 138)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# ---- precomputed polar coordinates for every pixel
PIX = [[(px - CX, py - CY,
         math.hypot(px - CX, py - CY),
         math.atan2(py - CY, px - CX)) for px in range(GW)] for py in range(GH)]


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def tomoe_cov(x, y, r, th, phi, g, hx, hy):
    """Coverage (0..1) of one comma-shaped tomoe at this pixel."""
    if g <= 0.01:
        return 0.0
    head = clamp(HEAD * g + 0.5 - math.hypot(x - hx, y - hy))
    d = (phi - th) % (2 * math.pi)       # tail trails behind the spin
    tail = 0.0
    if d < TAIL_ANGLE:
        f = d / TAIL_ANGLE
        hw = HEAD * 0.95 * g * (1 - f)
        rc = ORBIT - 2.8 * f             # tail curls inward
        tail = clamp(hw + 0.5 - abs(r - rc))
    return head if head > tail else tail


def pixel(px, py, S):
    x, y, r, th = PIX[py][px]
    if abs(x) > W_HALF:
        return BG
    hl = max(S["open"] * H_HALF * (1 - (x / (W_HALF + 0.5)) ** 2) ** 0.75, 0.8)
    ay = abs(y)
    if ay > hl:
        return BG
    if ay > hl - 1.3:
        return LID

    rn = S["rn"]
    # sclera with shading toward lids and corners
    shade = min(1.0, (ay / hl) ** 3 + (abs(x) / W_HALF) ** 4)
    col = mix(SCLERA, SCLERA_EDGE, shade)

    if r <= IR:
        t = r / IR
        col = mix(mix(RED_IN, RED_OUT, t ** 1.5), mix(PUR_IN, PUR_OUT, t ** 1.2), rn)
        if r > IR - 1.3:
            col = mix(col, mix(LIMB_RED, LIMB_PUR, rn), 0.85)

        # Rinnegan ripples spreading outward
        if rn > 0:
            for rr in RINGS:
                ap = clamp((rn * (IR + 2) - rr) / 1.5)
                if ap > 0:
                    c = clamp(0.95 - abs(r - rr)) * ap
                    if c > 0:
                        col = mix(col, RING_COL, c * 0.9)

        # Sharingan ring + tomoe
        ta = S["tomoe_amt"]
        if ta > 0:
            col = mix(col, BLACK, clamp(0.9 - abs(r - RING_R)) * ta)
            cov = 0.0
            for phi, g, hx, hy in S["tomoe"]:
                c = tomoe_cov(x, y, r, th, phi, g, hx, hy)
                if c > cov:
                    cov = c
            col = mix(col, BLACK, cov * ta)

        # Mangekyou: three tapering, curved blades
        mk = S["mk"]
        if mk > 0 and PUPIL < r <= MK_OUT * mk:
            thr = -0.3 + 1.3 * (r / MK_OUT)
            u = 3 * (th + S["spin"]) - 0.30 * r
            a = clamp((math.cos(u) - thr) * 5)
            if a > 0:
                col = mix(col, BLACK, a * (1 - rn))

        # pupil
        col = mix(col, BLACK, clamp(PUPIL + 0.5 - r))

    # shadow cast by the upper lid
    if y < 0:
        d = hl - ay
        k = 1 - 0.4 * clamp(1 - d / 5)
        col = (col[0] * k, col[1] * k, col[2] * k)

    # wet highlight
    h = clamp((1.8 - math.hypot(x + 4.5, y + 5.0)) / 1.0)
    if h > 0:
        col = mix(col, WHITE, h * 0.75)

    return (int(col[0]), int(col[1]), int(col[2]))


# ---- timeline (in frames) -------------------------------------------------
OPEN_END = 36
B0, B1 = 120, 156        # 3rd tomoe appears
C0, C1 = 240, 288        # -> Mangekyou
D0, D1 = 360, 420        # -> Rinnegan
CLOSE0, CLOSE1 = 540, 564
CYCLE = 576


def timeline(f, spin):
    if f < CLOSE0:
        op = smooth(f / OPEN_END)
    else:
        op = 1 - smooth((f - CLOSE0) / (CLOSE1 - CLOSE0))

    g12 = smooth((f - 10) / 30)
    pB = smooth((f - B0) / (B1 - B0))
    pC = smooth((f - C0) / (C1 - C0))
    pD = smooth((f - D0) / (D1 - D0))
    spacing = math.pi - (math.pi / 3) * pB          # 180 deg -> 120 deg

    tomoe = []
    for i, g in ((0, g12), (1, g12), (2, pB)):
        phi = spin + i * spacing - math.pi / 2
        tomoe.append((phi, g, ORBIT * math.cos(phi), ORBIT * math.sin(phi)))

    speed = (0.07 + 0.22 * math.sin(math.pi * pB) + 0.25 * math.sin(math.pi * pC)) * (1 - 0.9 * pD)

    S = {"open": op, "tomoe": tomoe, "tomoe_amt": 1 - pC,
         "mk": pC, "rn": pD, "spin": spin}

    if f < B0:
        cap = ("SHARINGAN", "2 TOMOE", (255, 70, 70))
    elif f < C0:
        cap = ("SHARINGAN", "3 TOMOE", (255, 70, 70))
    elif f < D0:
        cap = ("MANGEKYOU SHARINGAN", "", (255, 40, 40))
    else:
        cap = ("RINNEGAN", "", (190, 150, 255))
    return S, speed, cap


def render(S, cap):
    out = ["\033[H"]
    for k in range(GH // 2):
        prev = None
        for px in range(GW):
            top = pixel(px, 2 * k, S)
            bot = pixel(px, 2 * k + 1, S)
            key = (top, bot)
            if key != prev:
                out.append("\033[38;2;%d;%d;%dm\033[48;2;%d;%d;%dm" % (top + bot))
                prev = key
            out.append("\u2580")
        out.append("\033[0m\033[K\n")
    title, sub, (r, g, b) = cap
    out.append("\033[38;2;%d;%d;%dm%s\033[0m\033[K\n" % (r, g, b, title.center(GW)))
    out.append("\033[38;2;150;150;150m%s\033[0m\033[K\n" % sub.center(GW))
    return "".join(out)


def main():
    if not sys.stdout.isatty():
        print("Run this in a real terminal (Windows Terminal / VS Code terminal / PowerShell).")
        return
    if os.name == "nt":
        os.system("")                      # enable ANSI colours on Windows
    sys.stdout.write("\033[2J\033[?25l")
    f, spin = 0, 0.0
    try:
        while True:
            t0 = time.time()
            S, speed, cap = timeline(f, spin)
            sys.stdout.write(render(S, cap))
            sys.stdout.flush()
            spin += speed
            f += 1
            if f >= CYCLE:
                if not LOOP:
                    break
                f = 0
            time.sleep(max(0.0, 1 / FPS - (time.time() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[0m\n")


if __name__ == "__main__":
    main()