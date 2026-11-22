"""
EYES OF POWER  -  Sharingan (1-2-3 tomoe) -> Mangekyou (Itachi) -> Mangekyou (Sasuke)
                  -> Eternal Mangekyou -> Byakugan -> Rinne-Sharingan -> Rinnegan

Full-colour terminal animation (24-bit colour + half-block pixels).
The eye automatically scales to fit your terminal window.

Run in Windows Terminal / VS Code terminal / PowerShell / any modern terminal:
    python sharingan.py            (auto size)
    python sharingan.py 1.6        (force a size; bigger = sharper, needs bigger window)
Ctrl+C to stop.
"""
import math
import os
import shutil
import sys
import time

FPS = 24
LOOP = True            # blink and replay forever
MAX_SCALE = 1.9

# ---------------------------------------------------------------- geometry (units)
W_HALF, H_HALF = 26, 17          # half width / half height of the eye opening
IR = 13.0                        # iris radius
PUPIL = 2.5
RING_R = 9.4                     # thin ring holding the tomoe
ORBIT, HEAD = 7.0, 2.2           # tomoe orbit radius / head radius
TAIL_ANGLE = 1.15
MK_OUT = 11.0                    # mangekyou reach
RINGS = (4.3, 6.8, 9.2, 11.4)    # rinnegan rings
TAU = math.tau

# ---------------------------------------------------------------- colours
BG = (8, 8, 12)
LID = (36, 20, 20)
SCLERA, SCLERA_EDGE = (247, 241, 239), (196, 160, 158)
RED_IN, RED_OUT, LIMB_RED = (240, 30, 30), (150, 0, 8), (58, 0, 6)
PUR_IN, PUR_OUT, LIMB_PUR = (200, 180, 244), (138, 110, 200), (72, 50, 118)
RING_COL = (80, 54, 136)
BYA_IN, BYA_OUT, LIMB_BYA = (240, 238, 252), (204, 197, 238), (148, 138, 200)
VEIN = (92, 78, 165)
BLACK, WHITE = (0, 0, 0), (255, 255, 255)

AURA = {"sha": (255, 25, 25), "itachi": (255, 25, 25), "sasuke": (255, 45, 25),
        "ems": (255, 70, 30), "bya": (150, 140, 255), "rsh": (205, 85, 255),
        "rin": (170, 110, 255)}

# ---------------------------------------------------------------- small helpers
def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


SCALE = 1.0
AA = 1.0
GW = GH = 0
CX = CY = 0.0
PIX = []


def setup(scale):
    """Build the pixel grid. 1 terminal cell = 1 pixel wide x 2 pixels tall."""
    global SCALE, AA, GW, GH, CX, CY, PIX
    SCALE, AA = scale, 1.0 / scale
    GW = int((2 * W_HALF + 3) * scale)
    GH = int(36 * scale / 2) * 2
    CX, CY = (GW - 1) / 2, (GH - 1) / 2
    PIX = []
    for py in range(GH):
        row = []
        for px in range(GW):
            x, y = (px - CX) / scale, (py - CY) / scale
            row.append((x, y, math.hypot(x, y), math.atan2(y, x)))
        PIX.append(row)


def cov(d, R):
    """Anti-aliased coverage: 1 when distance d is well inside R, 0 well outside."""
    return clamp(0.5 + (R - d) / AA)


# ---------------------------------------------------------------- iris building blocks
def red_base(r, th):
    t = r / IR
    c = mix(RED_IN, RED_OUT, t ** 1.5)
    k = 1 + 0.07 * math.sin(th * 19 + 1.0) + 0.05 * math.sin(th * 43)     # iris fibres
    c = (min(255, c[0] * k), c[1] * k, c[2] * k)
    return mix(c, LIMB_RED, clamp(0.5 + (r - (IR - 1.3)) / AA) * 0.85)


def purple_base(r, th):
    t = r / IR
    c = mix(PUR_IN, PUR_OUT, t ** 1.2)
    return mix(c, LIMB_PUR, clamp(0.5 + (r - (IR - 1.3)) / AA) * 0.85)


def add_rings(col, r):
    for rr in RINGS:
        col = mix(col, RING_COL, cov(abs(r - rr), 0.45) * 0.9)
    return col


def add_pupil(col, r):
    return mix(col, BLACK, cov(r, PUPIL))


def tomoe_cov(x, y, r, th, t):
    phi, g, hx, hy, orb, head = t
    if g <= 0.01:
        return 0.0
    h = cov(math.hypot(x - hx, y - hy), head * g)
    d = (phi - th) % TAU                       # tail trails behind the spin
    tl = 0.0
    ta = 3.66 * head / orb                     # tail length scales with the tomoe size
    if d < ta:
        f = d / ta
        tl = cov(abs(r - (orb - 0.4 * orb * f)), head * 0.95 * g * (1 - f))
    return h if h > tl else tl


def spikes(r, th, spin, width, expo, twist, disc, tip):
    """Three tapering spear-blades (Sasuke-style)."""
    if r >= tip:
        return 0.0
    a = (th + spin + twist * r) % (TAU / 3)
    ang = min(a, TAU / 3 - a)
    s = clamp((r - disc * 0.8) / (tip - disc * 0.8))
    hw = width * (1 - s) ** expo
    return clamp(0.5 + (hw - ang) * r / AA)


# ---------------------------------------------------------------- the eyes
def eye_sha(x, y, r, th, S):
    col = red_base(r, th)
    col = mix(col, BLACK, cov(abs(r - RING_R), 0.4))
    m = 0.0
    for t in S["tomoe"]:
        c = tomoe_cov(x, y, r, th, t)
        if c > m:
            m = c
    return add_pupil(mix(col, BLACK, m), r)


def eye_itachi(x, y, r, th, S):
    col = red_base(r, th)
    if PUPIL < r <= MK_OUT:
        u = 3 * (th + S["spin"]) - 0.30 * r
        thr = -0.3 + 1.3 * (r / MK_OUT)
        col = mix(col, BLACK, clamp((math.cos(u) - thr) * 5 * SCALE))
    return add_pupil(col, r)


def eye_sasuke(x, y, r, th, S):
    col = red_base(r, th)
    a = max(spikes(r, th, S["spin"], 0.62, 1.0, 0.10, 4.0, MK_OUT), cov(r, 4.0))
    col = mix(col, BLACK, a)
    return add_pupil(col, r)


def eye_ems(x, y, r, th, S):
    col = red_base(r, th)
    col = mix(col, BLACK, cov(abs(r - 11.7), 0.45))                      # outer rim
    a = max(spikes(r, th, S["spin"], 0.92, 0.8, 0.17, 5.0, 11.2), cov(r, 5.0))
    col = mix(col, BLACK, a)
    col = mix(col, (200, 20, 20), cov(r, 3.4) * 0.9)                     # red eye in the centre
    return add_pupil(col, r)


def eye_bya(x, y, r, th, S):
    t = r / IR
    col = mix(BYA_IN, BYA_OUT, t ** 2)
    col = mix(col, LIMB_BYA, clamp(0.5 + (r - (IR - 1.3)) / AA) * 0.85)
    col = mix(col, (190, 184, 226), cov(r, PUPIL) * 0.6)                 # faint pupil
    return mix(col, (170, 162, 214), cov(abs(r - PUPIL), 0.4) * 0.8)


def eye_rsh(x, y, r, th, S):
    col = add_rings(purple_base(r, th), r)
    m = 0.0
    for t in S["tomoe9"]:
        c = tomoe_cov(x, y, r, th, t)
        if c > m:
            m = c
    return add_pupil(mix(col, BLACK, m), r)


def eye_rin(x, y, r, th, S):
    return add_pupil(add_rings(purple_base(r, th), r), r)


EYE = {"sha": eye_sha, "itachi": eye_itachi, "sasuke": eye_sasuke, "ems": eye_ems,
       "bya": eye_bya, "rsh": eye_rsh, "rin": eye_rin}


def iris_color(x, y, r, th, S):
    """Crossfade between the previous and current eye: the new eye spreads outward from the pupil."""
    p = S["p"]
    if p >= 1:
        return EYE[S["cur"]](x, y, r, th, S)
    w = clamp((p * (IR + 4) - r) / 3)
    if w <= 0:
        return EYE[S["prev"]](x, y, r, th, S)
    if w >= 1:
        return EYE[S["cur"]](x, y, r, th, S)
    return mix(EYE[S["prev"]](x, y, r, th, S), EYE[S["cur"]](x, y, r, th, S), w)


# ---------------------------------------------------------------- one pixel
def pixel(px, py, S):
    x, y, r, th = PIX[py][px]

    g = clamp(1 - r / (W_HALF * 1.25)) ** 2 * 0.55                       # coloured aura
    au = S["aura"]
    bg = (BG[0] + au[0] * g, BG[1] + au[1] * g, BG[2] + au[2] * g)

    if abs(x) > W_HALF + 0.5:
        return _rgb(bg)
    hl = max(S["open"] * H_HALF * (1 - (x / (W_HALF + 0.5)) ** 2) ** 0.75, 0.8)
    ay = abs(y)
    a = clamp(0.5 + (hl - ay) / AA)
    if a <= 0:
        return _rgb(bg)

    # sclera (white of the eye), shaded toward lids and corners
    shade = min(1.0, (ay / hl) ** 3 + (abs(x) / W_HALF) ** 4)
    col = mix(SCLERA, SCLERA_EDGE, shade)

    # Byakugan veins
    if S["bya"] > 0 and r > IR:
        v = abs(math.sin(th * 9 + r * 0.5))
        line = clamp(1 - v / 0.16) * clamp(1.2 - (r - IR) / 18) * S["bya"] * 0.95
        if line > 0:
            col = mix(col, VEIN, line)

    # iris
    if r <= IR + AA:
        col = mix(col, iris_color(x, y, r, th, S), clamp(0.5 + (IR - r) / AA))

    # wet highlights
    if r < IR + 1:
        col = mix(col, WHITE, cov(math.hypot(x + 4.5, y + 5.0), 1.7) * 0.78)
        col = mix(col, WHITE, cov(math.hypot(x - 5.0, y - 4.0), 0.9) * 0.35)

    # shadow cast by the upper lid
    if y < 0:
        k = 1 - 0.4 * clamp(1 - (hl - ay) / 5)
        col = (col[0] * k, col[1] * k, col[2] * k)

    # lash line
    col = mix(col, LID, clamp(0.5 + (ay - (hl - 1.3)) / AA))
    if a < 1:
        col = mix(bg, col, a)
    return _rgb(col)


def _rgb(c):
    return (max(0, min(255, int(c[0]))), max(0, min(255, int(c[1]))), max(0, min(255, int(c[2]))))


# ---------------------------------------------------------------- timeline (frames @ FPS)
EYES = ["itachi", "sasuke", "ems", "bya", "rsh", "rin"]
SH_END = 252                      # sharingan block (1 -> 2 -> 3 tomoe) ends
TRANS, SEG = 30, 114              # transition length / length of each later eye
CLOSE0 = SH_END + 5 * SEG + TRANS + 130
CLOSE1 = CLOSE0 + 24
CYCLE = CLOSE1 + 24

RED, PURPLE, LAV = (255, 70, 70), (200, 130, 255), (190, 180, 255)
CAPTIONS = [
    ("S H A R I N G A N", "1 TOMOE", RED),
    ("S H A R I N G A N", "2 TOMOE", RED),
    ("S H A R I N G A N", "3 TOMOE", RED),
    ("M A N G E K Y O U   S H A R I N G A N", "Itachi Uchiha", (255, 40, 40)),
    ("M A N G E K Y O U   S H A R I N G A N", "Sasuke Uchiha", (255, 50, 40)),
    ("E T E R N A L   M A N G E K Y O U", "Sasuke Uchiha", (255, 80, 40)),
    ("B Y A K U G A N", "Hyuga Clan", LAV),
    ("R I N N E - S H A R I N G A N", "Madara Uchiha", PURPLE),
    ("R I N N E G A N", "Eye of the Six Paths", PURPLE),
]

BURSTS = [(84, 24), (168, 24)] + [(SH_END + i * SEG, TRANS) for i in range(len(EYES))]


def timeline(f, spin):
    op = smooth(f / 36) if f < CLOSE0 else 1 - smooth((f - CLOSE0) / (CLOSE1 - CLOSE0))

    # tomoe count 0 -> 1 -> 2 -> 3 (fractional while growing)
    c = smooth((f - 8) / 28) + smooth((f - 84) / 24) + smooth((f - 168) / 24)
    spacing = TAU / max(c, 1.0)
    tomoe = []
    for i in range(3):
        phi = spin + i * spacing - math.pi / 2
        tomoe.append((phi, clamp(c - i), ORBIT * math.cos(phi), ORBIT * math.sin(phi), ORBIT, HEAD))

    # nine tomoe for the Rinne-Sharingan (3 rings of 3)
    t9 = []
    for j, (orb, hd) in enumerate(((5.2, 1.25), (8.0, 1.5), (10.8, 1.7))):
        for i in range(3):
            phi = spin + i * TAU / 3 + j * 0.75 - math.pi / 2
            t9.append((phi, 1.0, orb * math.cos(phi), orb * math.sin(phi), orb, hd))

    if f < SH_END:
        prev = cur = "sha"
        p = 1.0
        stage = 0 if f < 96 else 1 if f < 180 else 2
    else:
        i = min(int((f - SH_END) // SEG), len(EYES) - 1)
        local = f - SH_END - i * SEG
        p = smooth(local / TRANS)
        cur = EYES[i]
        prev = "sha" if i == 0 else EYES[i - 1]
        stage = 3 + i if p >= 0.5 else 2 + i

    bya = p if cur == "bya" else (1 - p) if prev == "bya" else 0.0
    burst = sum(math.sin(math.pi * clamp((f - a) / d)) for a, d in BURSTS)
    speed = 0.07 + 0.2 * burst

    S = {"open": op, "tomoe": tomoe, "tomoe9": t9, "prev": prev, "cur": cur, "p": p,
         "bya": bya, "spin": spin, "aura": mix(AURA[prev], AURA[cur], p)}
    return S, speed, stage


# ---------------------------------------------------------------- terminal rendering
def render(S, stage):
    out = ["\033[H"]
    for k in range(GH // 2):
        prev = None
        for px in range(GW):
            top, bot = pixel(px, 2 * k, S), pixel(px, 2 * k + 1, S)
            key = (top, bot)
            if key != prev:
                out.append("\033[38;2;%d;%d;%dm\033[48;2;%d;%d;%dm" % (top + bot))
                prev = key
            out.append("\u2580")
        out.append("\033[0m\033[K\n")
    title, sub, (r, g, b) = CAPTIONS[stage]
    out.append("\033[1;38;2;%d;%d;%dm%s\033[0m\033[K\n" % (r, g, b, title.center(GW)))
    out.append("\033[38;2;160;160;170m%s\033[0m\033[K\n" % sub.center(GW))
    dots = []
    for i in range(len(CAPTIONS)):
        if i == stage:
            dots.append("\033[38;2;%d;%d;%dm\u25cf\033[0m" % (r, g, b))
        else:
            dots.append("\033[38;2;90;90;100m\u25cb\033[0m")
    out.append(" " * ((GW - (2 * len(CAPTIONS) - 1)) // 2) + " ".join(dots) + "\033[K\n")
    return "".join(out)


def main():
    if not sys.stdout.isatty():
        print("Run this in a real terminal (Windows Terminal / VS Code terminal / PowerShell).")
        return
    if os.name == "nt":
        os.system("")                                   # enable ANSI colours on Windows
    cols, lines = shutil.get_terminal_size((100, 30))
    if len(sys.argv) > 1:
        scale = float(sys.argv[1])
    else:
        scale = min((cols - 1) / (2 * W_HALF + 3), 2 * (lines - 4) / 36, MAX_SCALE)
    scale = max(0.6, scale)
    setup(scale)

    sys.stdout.write("\033[2J\033[?25l")
    start = last = time.time()
    spin = 0.0
    try:
        while True:
            now = time.time()
            f = (now - start) * FPS
            if f >= CYCLE:
                if not LOOP:
                    break
                start, f, spin = now, 0.0, 0.0
            S, speed, stage = timeline(f, spin)
            spin += speed * (now - last) * FPS
            last = now
            sys.stdout.write(render(S, stage))
            sys.stdout.flush()
            time.sleep(max(0.0, 1 / FPS - (time.time() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[0m\n")


if __name__ == "__main__":
    main()