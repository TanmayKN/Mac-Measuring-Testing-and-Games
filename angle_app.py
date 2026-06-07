#!/opt/homebrew/bin/python3.11
"""MacBook Tilt App — Measurement mode + Flappy Bird. Run with sudo."""

import pygame, math, sys, time, threading, random
from macimu import IMU

# ── sensor ────────────────────────────────────────────────────────────────────
try:
    imu = IMU(accel=True, gyro=True, lid=True)
    imu.start()
except PermissionError:
    print("\nRun with sudo:\n  sudo /opt/homebrew/bin/python3.11 ~/angle_detector/angle_app.py\n")
    sys.exit(1)

time.sleep(0.5)

_ax = _ay = _az = 0.0
_gx = _gy = _gz = 0.0
_lid_cached = None
_lock = threading.Lock()

def _poll():
    global _ax, _ay, _az, _gx, _gy, _gz, _lid_cached
    while True:
        a   = imu.latest_accel()
        g   = imu.latest_gyro()
        lid = imu.read_lid()
        with _lock:
            if a:  _ax, _ay, _az = a.x, a.y, a.z
            if g:  _gx, _gy, _gz = g.x, g.y, g.z
            if lid is not None: _lid_cached = lid
        time.sleep(0.04)

threading.Thread(target=_poll, daemon=True).start()

def sensor_data():
    with _lock:
        ax, ay, az = _ax, _ay, _az
        gx, gy, gz = _gx, _gy, _gz
        lid = _lid_cached
    tilt  = math.degrees(math.atan2(math.sqrt(ax*ax + ay*ay), abs(az)))
    pitch = math.degrees(math.atan2(-ax, math.sqrt(ay*ay + az*az)))
    roll  = math.degrees(math.atan2( ay, math.sqrt(ax*ax + az*az)))
    return tilt, pitch, roll, gx, gy, gz, lid

# ── pygame init ───────────────────────────────────────────────────────────────
pygame.init()
W, H = 480, 640
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Screen Tilt")
clock = pygame.time.Clock()

# fonts
F_TITLE  = pygame.font.SysFont("Helvetica Neue", 52, bold=True)
F_BIG    = pygame.font.SysFont("Helvetica Neue", 90, bold=True)
F_MED    = pygame.font.SysFont("Helvetica Neue", 32, bold=True)
F_SM     = pygame.font.SysFont("Helvetica Neue", 14)
F_MONO   = pygame.font.SysFont("Courier New",    12)
F_SCORE  = pygame.font.SysFont("Helvetica Neue", 64, bold=True)
F_MENU   = pygame.font.SysFont("Helvetica Neue", 26, bold=True)
F_SUB    = pygame.font.SysFont("Helvetica Neue", 15)

# colours
BG      = ( 15,  15,  15)
GREEN   = (  0, 230, 118)
YEL     = (255, 230,   0)
RED     = (255,  23,  68)
CYAN    = (  0, 229, 255)
DIM     = ( 50,  50,  50)
MID     = ( 90,  90,  90)
WHITE   = (255, 255, 255)
SKY     = ( 80, 180, 255)
PIPE_G  = ( 50, 200,  80)
PIPE_DK = ( 30, 140,  50)
GROUND  = (210, 180, 100)
GROUND2 = (180, 140,  70)
BIRD_Y  = (255, 220,  50)
BIRD_O  = (255, 140,   0)

def col(a):
    a = abs(a)
    if a < 5:  return GREEN
    if a < 20: return YEL
    return RED

def tc(surf, text, font, color, cx, y):
    s = font.render(text, True, color)
    surf.blit(s, (cx - s.get_width()//2, y))
    return s.get_height()

def tl(surf, text, font, color, x, y):
    surf.blit(font.render(text, True, color), (x, y))

def draw_arc(surf, cx, cy, r, a0, a1, color, w=4):
    steps = max(2, abs(int(a1-a0)))
    pts = [(cx+r*math.cos(math.radians(a0+(a1-a0)*i/steps)),
            cy-r*math.sin(math.radians(a0+(a1-a0)*i/steps)))
           for i in range(steps+1)]
    if len(pts) > 1:
        pygame.draw.lines(surf, color, False, pts, w)

def draw_rounded_rect(surf, color, rect, radius=12):
    pygame.draw.rect(surf, color, rect, border_radius=radius)

BACK_RECT = pygame.Rect(10, 10, 90, 32)

def draw_back_btn(surf):
    pygame.draw.rect(surf, (40, 40, 40), BACK_RECT, border_radius=8)
    pygame.draw.rect(surf, MID,          BACK_RECT, 1, border_radius=8)
    s = F_SM.render("← Menu", True, WHITE)
    surf.blit(s, (BACK_RECT.x + (BACK_RECT.w - s.get_width())//2,
                  BACK_RECT.y + (BACK_RECT.h - s.get_height())//2))

def back_clicked(events):
    """Return True if the back button was clicked or Esc pressed."""
    for e in events:
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and BACK_RECT.collidepoint(e.pos):
            return True
    return False

# ══════════════════════════════════════════════════════════════════════════════
#  MENU
# ══════════════════════════════════════════════════════════════════════════════
def run_menu():
    selected = 0
    btn_rects = [
        pygame.Rect(W//2-160, 220, 320, 68),
        pygame.Rect(W//2-160, 308, 320, 68),
        pygame.Rect(W//2-160, 396, 320, 68),
    ]
    labels   = ["📐  Measurement", "🐦  Flappy Tilt", "🪁  Plappy Constant"]
    subtexts = ["Live angle & tilt gauge",
                "Tilt UP to flap  •  Space to flap",
                "Screen angle = bird height (direct)"]
    anim = 0.0

    while True:
        dt = clock.tick(60) / 1000
        anim += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: imu.stop(); pygame.quit(); sys.exit()
                if e.key == pygame.K_UP:
                    selected = (selected - 1) % 3
                if e.key == pygame.K_DOWN:
                    selected = (selected + 1) % 3
                if e.key == pygame.K_RETURN:
                    return selected
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(btn_rects):
                    if r.collidepoint(e.pos): selected = i
            if e.type == pygame.MOUSEBUTTONDOWN:
                for i, r in enumerate(btn_rects):
                    if r.collidepoint(e.pos): return i

        screen.fill(BG)

        # animated title glow
        g = int(180 + 60 * math.sin(anim * 2))
        title_col = (0, g, min(255, g+60))
        tc(screen, "SCREEN TILT", F_TITLE, title_col, W//2, 80)
        tc(screen, "Choose a mode", F_SM, MID, W//2, 148)

        # sensor status pill
        _, _, _, _, _, _, lid = sensor_data()
        s_col = GREEN if lid is not None else YEL
        s_txt = f"sensor ready  {lid:.0f}°" if lid else "open lid slightly to wake sensor"
        pygame.draw.rect(screen, DIM, (W//2-140, 170, 280, 28), border_radius=14)
        tc(screen, s_txt, F_SM, s_col, W//2, 177)

        for i, (rect, label, sub) in enumerate(zip(btn_rects, labels, subtexts)):
            active = (i == selected)
            bg_col = (30, 30, 30) if not active else (0, 55, 75)
            border  = CYAN if active else DIM
            draw_rounded_rect(screen, bg_col, rect, 16)
            pygame.draw.rect(screen, border, rect, 2, border_radius=16)
            tc(screen, label, F_MENU, WHITE if active else MID, W//2, rect.y+10)
            tc(screen, sub,   F_SUB,  CYAN  if active else DIM,  W//2, rect.y+40)

        tc(screen, "↑↓ or mouse to select  •  Enter to launch", F_SM, DIM, W//2, 490)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  MEASUREMENT MODE
# ══════════════════════════════════════════════════════════════════════════════
def run_measure():
    while True:
        clock.tick(30)
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
        if back_clicked(events): return

        tilt, pitch, roll, gx, gy, gz, lid = sensor_data()
        screen.fill(BG)

        tc(screen, "LID / SCREEN ANGLE", F_SM, MID, W//2, 18)
        lid_str = f"{lid:.1f}°" if lid is not None else "---"
        lid_c   = col(abs(lid - 90)) if lid else DIM
        tc(screen, lid_str, F_BIG, lid_c, W//2, 30)

        CX, CY, R = W//2, 310, 115
        draw_arc(screen, CX, CY, R, 0, 180, DIM, 3)
        for d in range(0, 181, 10):
            rad = math.radians(d)
            inner = R-(14 if d%30==0 else 6)
            pygame.draw.line(screen, DIM if d%30 else MID,
                (int(CX+inner*math.cos(rad)), int(CY-inner*math.sin(rad))),
                (int(CX+R*math.cos(rad)),     int(CY-R*math.sin(rad))), 1)
            if d % 30 == 0:
                lb = F_SM.render(f"{d}°", True, MID)
                screen.blit(lb, (int(CX+(R-22)*math.cos(rad)-lb.get_width()//2),
                                 int(CY-(R-22)*math.sin(rad)-lb.get_height()//2)))

        if lid is not None:
            sweep = max(0., min(180., lid))
            draw_arc(screen, CX, CY, R, 0, sweep, lid_c, 5)
            rad = math.radians(sweep)
            nx, ny = int(CX+(R-8)*math.cos(rad)), int(CY-(R-8)*math.sin(rad))
            pygame.draw.line(screen, lid_c, (CX, CY), (nx, ny), 5)
            pygame.draw.circle(screen, lid_c, (nx, ny), 9)
        pygame.draw.circle(screen, CYAN, (CX, CY), 6)

        tl(screen, "BODY TILT", F_SM, MID, 55, 350)
        tl(screen, f"{tilt:.1f}°", F_MED, col(tilt), 55, 365)
        tl(screen, "ROLL", F_SM, MID, 270, 350)
        tl(screen, f"{roll:+.1f}°", F_MED, col(roll), 270, 365)

        tc(screen, f"gyro  x{gx:+.2f}  y{gy:+.2f}  z{gz:+.2f}  °/s", F_MONO, DIM, W//2, 430)

        hint = "open/close lid to wake sensor" if lid is None else \
               ("lid closed" if lid < 10 else f"{lid:.1f}° open")
        tc(screen, hint, F_SM, MID, W//2, 458)
        draw_back_btn(screen)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  FLAPPY BIRD
# ══════════════════════════════════════════════════════════════════════════════
GROUND_Y   = H - 80
PIPE_W     = 70
PIPE_GAP   = 160
PIPE_SPEED  = 220   # px/s
GRAVITY     = 600   # px/s²  (lower = floatier, easier to control)
FLAP_VEL    = -280  # px/s  (upward impulse — softer jump)
BIRD_X      = 100
BIRD_R      = 18
FLAP_THRESH = 4     # degrees change to trigger flap (more responsive)

def draw_bird(surf, x, y, vel):
    # body
    pygame.draw.circle(surf, BIRD_Y, (int(x), int(y)), BIRD_R)
    pygame.draw.circle(surf, BIRD_O, (int(x), int(y)), BIRD_R, 3)
    # eye
    pygame.draw.circle(surf, WHITE, (int(x)+8, int(y)-6), 6)
    pygame.draw.circle(surf, (30,30,30), (int(x)+10, int(y)-6), 3)
    # beak
    beak = [
        (int(x)+BIRD_R-2, int(y)-2),
        (int(x)+BIRD_R+10, int(y)+2),
        (int(x)+BIRD_R-2, int(y)+6),
    ]
    pygame.draw.polygon(surf, BIRD_O, beak)
    # wing (flaps when going up)
    wing_y = int(y) + (4 if vel < 0 else 10)
    pygame.draw.ellipse(surf, BIRD_O,
        (int(x)-14, wing_y-6, 22, 12))

def draw_pipe(surf, px, gap_top, gap_bot):
    cap_h = 24
    # top pipe
    pygame.draw.rect(surf, PIPE_G,  (px, 0, PIPE_W, gap_top))
    pygame.draw.rect(surf, PIPE_DK, (px-4, gap_top-cap_h, PIPE_W+8, cap_h),
                     border_bottom_left_radius=6, border_bottom_right_radius=6)
    # bottom pipe
    pygame.draw.rect(surf, PIPE_G,  (px, gap_bot, PIPE_W, H-gap_bot))
    pygame.draw.rect(surf, PIPE_DK, (px-4, gap_bot, PIPE_W+8, cap_h),
                     border_top_left_radius=6, border_top_right_radius=6)

def draw_ground(surf):
    pygame.draw.rect(surf, GROUND,  (0, GROUND_Y, W, H-GROUND_Y))
    pygame.draw.rect(surf, GROUND2, (0, GROUND_Y, W, 8))

def run_game():
    # state
    bird_y   = H // 2
    bird_vel = 0.0
    pipes    = []   # list of [x, gap_top, gap_bot, scored]
    score    = 0
    alive    = True
    started  = False
    hi_score = 0
    flash    = 0.0

    # tilt flap detection
    last_lid     = None
    lid_baseline = None

    def spawn_pipe():
        gap_top = random.randint(120, GROUND_Y - PIPE_GAP - 80)
        pipes.append([W + PIPE_W, gap_top, gap_top + PIPE_GAP, False])

    spawn_pipe()

    # cloud positions (decorative)
    clouds = [(random.randint(0, W), random.randint(40, 160)) for _ in range(4)]
    ground_scroll = 0.0

    def reset():
        nonlocal bird_y, bird_vel, pipes, score, alive, started
        nonlocal last_lid, lid_baseline, ground_scroll, flash
        bird_y = H // 2; bird_vel = 0.0
        pipes.clear(); spawn_pipe()
        score = 0; alive = True; started = False
        last_lid = None; lid_baseline = None
        ground_scroll = 0.0; flash = 0.0

    while True:
        dt = clock.tick(60) / 1000
        flash = max(0.0, flash - dt * 3)

        # ── events ──
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    if not alive: reset()
                if e.key == pygame.K_SPACE:
                    if not alive: reset()
                    else:
                        started = True
                        bird_vel = FLAP_VEL
        if back_clicked(events): return

        # ── tilt flap — upward tilt only ──
        _, _, _, _, _, _, lid = sensor_data()
        if lid is not None:
            if lid_baseline is None:
                lid_baseline = lid
            if last_lid is not None:
                delta = lid - last_lid
                # only positive delta (opening lid / tilting up) triggers flap
                if delta >= FLAP_THRESH:
                    if not alive:
                        reset()
                    else:
                        started = True
                        bird_vel = FLAP_VEL
            last_lid = lid

        # ── physics ──
        if alive and started:
            bird_vel    += GRAVITY * dt
            bird_y      += bird_vel * dt
            ground_scroll = (ground_scroll + PIPE_SPEED * dt) % 40

            # move pipes
            for p in pipes:
                p[0] -= PIPE_SPEED * dt

            # score
            for p in pipes:
                if not p[3] and p[0] + PIPE_W < BIRD_X:
                    p[3] = True; score += 1
                    if score > hi_score: hi_score = score

            # remove off-screen, spawn new
            pipes = [p for p in pipes if p[0] > -PIPE_W - 20]
            if pipes[-1][0] < W - 260:
                spawn_pipe()

            # collision
            br = BIRD_R - 3
            if bird_y - br < 0 or bird_y + br > GROUND_Y:
                alive = False; flash = 1.0
            for p in pipes:
                px, gt, gb, _ = p
                in_x = px - br < BIRD_X + br and px + PIPE_W + br > BIRD_X - br
                in_y = bird_y - br < gt or bird_y + br > gb
                if in_x and in_y:
                    alive = False; flash = 1.0

        # ── draw sky ──
        screen.fill(SKY)

        # clouds
        for cx, cy in clouds:
            pygame.draw.ellipse(screen, WHITE, (cx-30, cy-15, 70, 30))
            pygame.draw.ellipse(screen, WHITE, (cx-10, cy-28, 50, 30))

        # pipes
        for p in pipes:
            draw_pipe(screen, int(p[0]), p[1], p[2])

        # ground
        draw_ground(screen)
        # ground stripes
        for i in range(-1, W//40 + 2):
            sx = int(i * 40 - ground_scroll)
            pygame.draw.rect(screen, GROUND2, (sx, GROUND_Y+8, 20, 8))

        # bird
        if alive or (not alive and int(time.time()*8) % 2 == 0):
            draw_bird(screen, BIRD_X, max(BIRD_R, min(GROUND_Y-BIRD_R, bird_y)), bird_vel)

        # flash overlay on death
        if flash > 0:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(flash * 180)))
            screen.blit(overlay, (0, 0))

        # score
        tc(screen, str(score), F_SCORE, WHITE, W//2, 30)

        # ── overlays ──
        if not started and alive:
            # start screen
            panel = pygame.Surface((320, 120), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 140))
            screen.blit(panel, (W//2-160, H//2-110))
            tc(screen, "FLAPPY TILT", F_TITLE, WHITE,  W//2, H//2-100)
            tc(screen, "Tilt screen UP to flap", F_SM, WHITE, W//2, H//2-48)
            tc(screen, "or press SPACE",          F_SM, CYAN,  W//2, H//2-28)

        if not alive:
            panel = pygame.Surface((300, 200), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 170))
            screen.blit(panel, (W//2-150, H//2-100))
            tc(screen, "GAME OVER", F_TITLE, RED,   W//2, H//2-90)
            tc(screen, f"Score: {score}",    F_MED,  WHITE, W//2, H//2-20)
            tc(screen, f"Best:  {hi_score}", F_MED,  YEL,   W//2, H//2+20)
            tc(screen, "Tilt UP / Space / Enter to restart", F_SM, CYAN, W//2, H//2+70)

        # tilt indicator (bottom-right corner)
        ind_txt = f"lid {lid:.0f}°" if lid else "no sensor"
        ind_col = GREEN if lid else RED
        tl(screen, ind_txt, F_SM, ind_col, W-90, H-24)

        draw_back_btn(screen)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  PLAPPY CONSTANT  — screen angle directly = bird Y position
# ══════════════════════════════════════════════════════════════════════════════
def run_plappy_constant():
    """Bird Y is directly proportional to lid angle. No flapping, no gravity."""
    pipes     = []
    score     = 0
    hi_score  = 0
    alive     = True
    started   = False
    flash     = 0.0
    ground_scroll = 0.0

    # calibration: record baseline angle when game starts
    lid_min   = None   # angle = bird at bottom
    lid_max   = None   # angle = bird at top
    CALIB_RANGE = 40.0  # degrees of lid movement = full screen travel

    def spawn_pipe():
        gap_top = random.randint(100, GROUND_Y - PIPE_GAP - 60)
        pipes.append([W + PIPE_W, gap_top, gap_top + PIPE_GAP, False])

    spawn_pipe()
    clouds = [(random.randint(0, W), random.randint(40, 160)) for _ in range(4)]

    def reset():
        nonlocal pipes, score, alive, started, flash, ground_scroll, lid_min, lid_max
        pipes.clear(); spawn_pipe()
        score = 0; alive = True; started = False
        flash = 0.0; ground_scroll = 0.0
        lid_min = None; lid_max = None

    bird_y = H // 2

    while True:
        dt = clock.tick(60) / 1000
        flash = max(0.0, flash - dt * 3)

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN and not alive: reset()
                if e.key == pygame.K_SPACE  and not alive: reset()
        if back_clicked(events): return

        # ── read lid, map to bird Y ──
        _, _, _, _, _, _, lid = sensor_data()
        if lid is not None:
            # set baseline on first reading
            if lid_min is None:
                lid_min = lid - CALIB_RANGE / 2
                lid_max = lid + CALIB_RANGE / 2

            # expand range if user tilts beyond it
            lid_min = min(lid_min, lid)
            lid_max = max(lid_max, lid)
            span = max(lid_max - lid_min, 10.0)

            # map: more open lid (larger angle) → higher on screen (smaller Y)
            t = (lid - lid_min) / span          # 0.0 = closed = bottom, 1.0 = open = top
            t = max(0.0, min(1.0, t))
            target_y = GROUND_Y - 20 - t * (GROUND_Y - 60)

            # smooth follow so it doesn't jitter
            bird_y += (target_y - bird_y) * min(1.0, dt * 18)

            if not started and abs(target_y - bird_y) < 80:
                started = True   # auto-start once sensor is clearly moving

        # ── game logic ──
        if alive and started:
            ground_scroll = (ground_scroll + PIPE_SPEED * dt) % 40
            for p in pipes: p[0] -= PIPE_SPEED * dt

            for p in pipes:
                if not p[3] and p[0] + PIPE_W < BIRD_X:
                    p[3] = True; score += 1
                    if score > hi_score: hi_score = score

            pipes = [p for p in pipes if p[0] > -PIPE_W - 20]
            if pipes[-1][0] < W - 260: spawn_pipe()

            br = BIRD_R - 3
            if bird_y - br < 0 or bird_y + br > GROUND_Y:
                alive = False; flash = 1.0
            for p in pipes:
                in_x = p[0] - br < BIRD_X + br and p[0] + PIPE_W + br > BIRD_X - br
                in_y = bird_y - br < p[1] or bird_y + br > p[2]
                if in_x and in_y:
                    alive = False; flash = 1.0

        # ── draw ──
        screen.fill(SKY)
        for cx, cy in clouds:
            pygame.draw.ellipse(screen, WHITE, (cx-30, cy-15, 70, 30))
            pygame.draw.ellipse(screen, WHITE, (cx-10, cy-28, 50, 30))

        for p in pipes: draw_pipe(screen, int(p[0]), p[1], p[2])
        draw_ground(screen)
        for i in range(-1, W//40+2):
            sx = int(i*40 - ground_scroll)
            pygame.draw.rect(screen, GROUND2, (sx, GROUND_Y+8, 20, 8))

        if alive or int(time.time()*8) % 2 == 0:
            draw_bird(screen, BIRD_X, max(BIRD_R, min(GROUND_Y-BIRD_R, bird_y)), 0)

        if flash > 0:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(flash * 180)))
            screen.blit(overlay, (0, 0))

        # score
        tc(screen, str(score), F_SCORE, WHITE, W//2, 30)

        # lid angle bar on left side
        if lid is not None:
            bar_h = GROUND_Y - 30
            bar_x = 18
            pygame.draw.rect(screen, DIM, (bar_x, 15, 10, bar_h), border_radius=5)
            t_clamped = max(0.0, min(1.0, (lid - (lid_min or lid)) / max(lid_max - (lid_min or lid), 10)))
            fill_y = 15 + bar_h - int(t_clamped * bar_h)
            pygame.draw.rect(screen, CYAN,
                (bar_x, fill_y, 10, 15 + bar_h - fill_y), border_radius=5)
            tl(screen, f"{lid:.0f}°", F_SM, CYAN, 6, fill_y - 16)

        if not started and alive:
            panel = pygame.Surface((340, 110), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 150))
            screen.blit(panel, (W//2-170, H//2-100))
            tc(screen, "PLAPPY CONSTANT",        F_TITLE, WHITE, W//2, H//2-95)
            tc(screen, "Screen angle = bird height", F_SM, WHITE, W//2, H//2-42)
            tc(screen, "Tilt to move — auto-starts", F_SM, CYAN,  W//2, H//2-22)

        if not alive:
            panel = pygame.Surface((300, 200), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 170))
            screen.blit(panel, (W//2-150, H//2-100))
            tc(screen, "GAME OVER", F_TITLE, RED,   W//2, H//2-90)
            tc(screen, f"Score: {score}",    F_MED,  WHITE, W//2, H//2-20)
            tc(screen, f"Best:  {hi_score}", F_MED,  YEL,   W//2, H//2+20)
            tc(screen, "Enter / Space to restart",   F_SM,  CYAN,  W//2, H//2+70)

        draw_back_btn(screen)
        pygame.display.flip()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
while True:
    choice = run_menu()
    if choice == 0:
        run_measure()
    elif choice == 1:
        run_game()
    else:
        run_plappy_constant()
