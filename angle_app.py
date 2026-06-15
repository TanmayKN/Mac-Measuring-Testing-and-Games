#!/opt/homebrew/bin/python3.11
"""MacBook Tilt App — Measurement · Flappy Tilt · Plappy Constant. Run with sudo."""

import pygame, math, sys, time, threading, random, json, os
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
        a = imu.latest_accel(); g = imu.latest_gyro(); lid = imu.read_lid()
        with _lock:
            if a:  _ax, _ay, _az = a.x, a.y, a.z
            if g:  _gx, _gy, _gz = g.x, g.y, g.z
            if lid is not None: _lid_cached = lid
        time.sleep(0.04)

threading.Thread(target=_poll, daemon=True).start()

def sensor_data():
    with _lock:
        ax,ay,az = _ax,_ay,_az; gx,gy,gz = _gx,_gy,_gz; lid = _lid_cached
    tilt  = math.degrees(math.atan2(math.sqrt(ax*ax+ay*ay), abs(az)))
    pitch = math.degrees(math.atan2(-ax, math.sqrt(ay*ay+az*az)))
    roll  = math.degrees(math.atan2( ay, math.sqrt(ax*ax+az*az)))
    return tilt, pitch, roll, gx, gy, gz, lid

# ── save / load ───────────────────────────────────────────────────────────────
SAVE_PATH = os.path.expanduser("~/.tilt_app_save.json")

def load_save():
    try:
        with open(SAVE_PATH) as f: return json.load(f)
    except Exception:
        return {"unlocked_skins": ["default"], "hi_scores": {}, "equipped": "default"}

def write_save(data):
    with open(SAVE_PATH, "w") as f: json.dump(data, f)

save = load_save()

# ── difficulty presets ────────────────────────────────────────────────────────
DIFFICULTIES = {
    "Easy":   dict(pipe_speed=120, pipe_gap=230, gravity=340,  flap_vel=-220, label="Easy",   color=(0,230,118)),
    "Normal": dict(pipe_speed=220, pipe_gap=160, gravity=600,  flap_vel=-280, label="Normal", color=(255,230,0)),
    "Hard":   dict(pipe_speed=310, pipe_gap=125, gravity=800,  flap_vel=-310, label="Hard",   color=(255,23,68)),
}
DIFF_ORDER = ["Easy", "Normal", "Hard"]

# ── skins ─────────────────────────────────────────────────────────────────────
# Each skin: (body_color, outline_color, eye_color, beak_color, wing_color, name, unlock_desc)
SKINS = {
    "default": dict(body=(255,220,50),  ring=(255,140,0),   eye=(255,255,255),
                    beak=(255,140,0),   wing=(255,140,0),   name="Classic",
                    desc="Always unlocked", unlock="default"),
    "fire":    dict(body=(255,80,20),   ring=(200,20,0),    eye=(255,200,100),
                    beak=(255,200,0),   wing=(200,20,0),    name="Fire",
                    desc="Score 5 on Normal+",  unlock="score_5_normal"),
    "ice":     dict(body=(100,220,255), ring=(0,150,220),   eye=(255,255,255),
                    beak=(200,240,255), wing=(0,180,255),   name="Ice",
                    desc="Score 5 in Plappy",   unlock="score_5_plappy"),
    "ghost":   dict(body=(220,220,230), ring=(150,150,170), eye=(80,80,100),
                    beak=(180,180,200), wing=(170,170,190), name="Ghost",
                    desc="Score 10 on any mode",unlock="score_10_any"),
    "gold":    dict(body=(255,200,0),   ring=(180,130,0),   eye=(255,255,255),
                    beak=(200,100,0),   wing=(180,130,0),   name="Gold",
                    desc="Score 15 on Normal+", unlock="score_15_normal"),
    "neon":    dict(body=(0,255,100),   ring=(0,180,60),    eye=(0,40,20),
                    beak=(0,230,80),    wing=(0,180,60),    name="Neon",
                    desc="Score 10 on Hard",    unlock="score_10_hard"),
}
SKIN_ORDER = ["default","fire","ice","ghost","gold","neon"]

def get_skin():
    return SKINS.get(save.get("equipped","default"), SKINS["default"])

def check_unlock(score, mode, diff):
    """Check and grant skin unlocks based on score/mode/diff. Returns list of newly unlocked."""
    newly = []
    unlocked = save.get("unlocked_skins", ["default"])
    diff_rank = DIFF_ORDER.index(diff) if diff in DIFF_ORDER else 1

    checks = {
        "fire":  score >= 5  and diff_rank >= 1 and mode == "flappy",
        "ice":   score >= 5  and mode == "plappy",
        "ghost": score >= 10,
        "gold":  score >= 15 and diff_rank >= 1,
        "neon":  score >= 10 and diff_rank == 2,
    }
    for skin_id, cond in checks.items():
        if cond and skin_id not in unlocked:
            unlocked.append(skin_id); newly.append(skin_id)
    save["unlocked_skins"] = unlocked
    write_save(save)
    return newly

# ── pygame ────────────────────────────────────────────────────────────────────
pygame.init()
W, H = 480, 640
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Screen Tilt")
clock = pygame.time.Clock()

F_TITLE = pygame.font.SysFont("Helvetica Neue", 52, bold=True)
F_BIG   = pygame.font.SysFont("Helvetica Neue", 90, bold=True)
F_MED   = pygame.font.SysFont("Helvetica Neue", 32, bold=True)
F_SM    = pygame.font.SysFont("Helvetica Neue", 14)
F_XSM   = pygame.font.SysFont("Helvetica Neue", 12)
F_MONO  = pygame.font.SysFont("Courier New",    12)
F_SCORE = pygame.font.SysFont("Helvetica Neue", 64, bold=True)
F_MENU  = pygame.font.SysFont("Helvetica Neue", 24, bold=True)
F_SUB   = pygame.font.SysFont("Helvetica Neue", 13)

BG     = ( 15, 15, 15);  GREEN  = (  0,230,118); YEL    = (255,230,  0)
RED    = (255, 23, 68);  CYAN   = (  0,229,255); DIM    = ( 50, 50, 50)
MID    = ( 90, 90, 90);  WHITE  = (255,255,255); SKY    = ( 80,180,255)
PIPE_G = ( 50,200, 80);  PIPE_DK= ( 30,140, 50); GROUND = (210,180,100)
GROUND2= (180,140, 70)

SKY_EASY   = ( 90, 190, 255)
SKY_NORMAL = ( 80, 180, 255)
SKY_HARD   = ( 40, 100, 180)

GROUND_Y = H - 80
BIRD_X   = 100
BIRD_R   = 18

def col(a):
    a = abs(a)
    if a < 5: return GREEN
    if a < 20: return YEL
    return RED

def tc(surf, text, font, color, cx, y):
    s = font.render(text, True, color)
    surf.blit(s, (cx - s.get_width()//2, y))

def tl(surf, text, font, color, x, y):
    surf.blit(font.render(text, True, color), (x, y))

def draw_arc(surf, cx, cy, r, a0, a1, color, w=4):
    steps = max(2, abs(int(a1-a0)))
    pts = [(cx+r*math.cos(math.radians(a0+(a1-a0)*i/steps)),
            cy-r*math.sin(math.radians(a0+(a1-a0)*i/steps)))
           for i in range(steps+1)]
    if len(pts) > 1:
        pygame.draw.lines(surf, color, False, pts, w)

BACK_RECT = pygame.Rect(10, 10, 90, 32)

def draw_back_btn(surf):
    pygame.draw.rect(surf, (40,40,40), BACK_RECT, border_radius=8)
    pygame.draw.rect(surf, MID,        BACK_RECT, 1,  border_radius=8)
    s = F_SM.render("← Menu", True, WHITE)
    surf.blit(s, (BACK_RECT.x+(BACK_RECT.w-s.get_width())//2,
                  BACK_RECT.y+(BACK_RECT.h-s.get_height())//2))

def back_clicked(events):
    for e in events:
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: return True
        if e.type == pygame.MOUSEBUTTONDOWN and BACK_RECT.collidepoint(e.pos): return True
    return False

# ── varied clouds ─────────────────────────────────────────────────────────────
def make_clouds(n=6):
    clouds = []
    for _ in range(n):
        x = random.randint(0, W)
        y = random.randint(30, 160)
        scale = random.uniform(0.6, 1.4)
        tint  = random.choice([(255,255,255),(240,245,255),(255,252,240),(230,240,255)])
        puffs = random.randint(2, 4)
        clouds.append(dict(x=x, y=y, scale=scale, tint=tint, puffs=puffs))
    return clouds

def draw_clouds(surf, clouds):
    for c in clouds:
        cx, cy, sc, tint, np_ = c["x"], c["y"], c["scale"], c["tint"], c["puffs"]
        # main body
        pygame.draw.ellipse(surf, tint,
            (int(cx-36*sc), int(cy-14*sc), int(72*sc), int(28*sc)))
        # extra puffs at varied offsets
        offsets = [(-22,-14),(10,-18),(24,-8),(-8,-20)]
        for i in range(np_):
            ox, oy = offsets[i % len(offsets)]
            r = int((14 + i*3) * sc)
            pygame.draw.circle(surf, tint,
                (int(cx+ox*sc), int(cy+oy*sc)), r)

# ── bird drawing ──────────────────────────────────────────────────────────────
def draw_bird(surf, x, y, vel, skin=None):
    if skin is None: skin = get_skin()
    by, bo, ey = skin["body"], skin["ring"], skin["eye"]
    bk, wg = skin["beak"], skin["wing"]

    pygame.draw.circle(surf, by, (int(x), int(y)), BIRD_R)
    pygame.draw.circle(surf, bo, (int(x), int(y)), BIRD_R, 3)
    pygame.draw.circle(surf, ey, (int(x)+8, int(y)-6), 6)
    pygame.draw.circle(surf, (30,30,30), (int(x)+10, int(y)-6), 3)
    beak_pts = [
        (int(x)+BIRD_R-2, int(y)-2),
        (int(x)+BIRD_R+10, int(y)+2),
        (int(x)+BIRD_R-2, int(y)+6),
    ]
    pygame.draw.polygon(surf, bk, beak_pts)
    wing_y = int(y) + (4 if vel < 0 else 10)
    pygame.draw.ellipse(surf, wg, (int(x)-14, wing_y-6, 22, 12))

def draw_pipe(surf, px, gap_top, gap_bot):
    cap_h = 24
    pygame.draw.rect(surf, PIPE_G,  (px, 0, 70, gap_top))
    pygame.draw.rect(surf, PIPE_DK, (px-4, gap_top-cap_h, 78, cap_h),
                     border_bottom_left_radius=6, border_bottom_right_radius=6)
    pygame.draw.rect(surf, PIPE_G,  (px, gap_bot, 70, H-gap_bot))
    pygame.draw.rect(surf, PIPE_DK, (px-4, gap_bot, 78, cap_h),
                     border_top_left_radius=6, border_top_right_radius=6)

def draw_ground(surf):
    pygame.draw.rect(surf, GROUND,  (0, GROUND_Y, W, H-GROUND_Y))
    pygame.draw.rect(surf, GROUND2, (0, GROUND_Y, W, 8))

# ── unlock toast ──────────────────────────────────────────────────────────────
class UnlockToast:
    def __init__(self): self.queue = []; self.timer = 0.0; self.current = None
    def add(self, skin_id):
        self.queue.append(skin_id)
    def update(self, dt):
        if self.current is None and self.queue:
            self.current = self.queue.pop(0); self.timer = 3.5
        if self.current:
            self.timer -= dt
            if self.timer <= 0: self.current = None
    def draw(self, surf):
        if not self.current: return
        sk = SKINS[self.current]
        alpha = min(1.0, self.timer) * min(1.0, 3.5-self.timer+0.5)
        panel = pygame.Surface((300, 56), pygame.SRCALPHA)
        panel.fill((20,20,20,int(220*alpha)))
        surf.blit(panel, (W//2-150, H-110))
        a = int(255*alpha)
        tc(surf, "🔓 SKIN UNLOCKED!", F_SM,  (255,200,0,a), W//2, H-104)
        tc(surf, sk["name"],          F_MED, (255,255,255),  W//2, H-86)

toast = UnlockToast()

# ══════════════════════════════════════════════════════════════════════════════
#  DIFFICULTY PICKER
# ══════════════════════════════════════════════════════════════════════════════
def pick_difficulty(mode_name):
    """Show Easy/Normal/Hard selector. Returns chosen diff string or None (back)."""
    sel = 1   # default Normal
    btn_w, btn_h = 260, 62
    btn_x = W//2 - btn_w//2
    btn_ys = [210, 290, 370]
    anim = 0.0

    while True:
        dt = clock.tick(60)/1000
        anim += dt
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP:   sel = (sel-1)%3
                if e.key == pygame.K_DOWN: sel = (sel+1)%3
                if e.key == pygame.K_RETURN: return DIFF_ORDER[sel]
            if e.type == pygame.MOUSEMOTION:
                for i,by in enumerate(btn_ys):
                    r = pygame.Rect(btn_x, by, btn_w, btn_h)
                    if r.collidepoint(e.pos): sel = i
            if e.type == pygame.MOUSEBUTTONDOWN:
                for i,by in enumerate(btn_ys):
                    r = pygame.Rect(btn_x, by, btn_w, btn_h)
                    if r.collidepoint(e.pos): return DIFF_ORDER[i]
        if back_clicked(events): return None

        screen.fill(BG)
        tc(screen, mode_name, F_TITLE, WHITE, W//2, 80)
        tc(screen, "Select difficulty", F_SM, MID, W//2, 146)

        for i, (dkey, by) in enumerate(zip(DIFF_ORDER, btn_ys)):
            d = DIFFICULTIES[dkey]
            active = (i == sel)
            dc = d["color"]
            bg_c = (30,30,30) if not active else (dc[0]//5, dc[1]//5, dc[2]//5)
            r = pygame.Rect(btn_x, by, btn_w, btn_h)
            pygame.draw.rect(screen, bg_c, r, border_radius=14)
            pygame.draw.rect(screen, dc if active else DIM, r, 2, border_radius=14)
            tc(screen, d["label"], F_MENU, dc if active else MID, W//2, by+10)
            hi_key = f"{dkey.lower()}"
            hi = save.get("hi_scores",{}).get(hi_key, {}).get("flappy", 0)
            hi2= save.get("hi_scores",{}).get(hi_key, {}).get("plappy", 0)
            hi_best = max(hi, hi2)
            sub = f"Best: {hi_best}" if hi_best else "no record yet"
            tc(screen, sub, F_XSM, CYAN if active else DIM, W//2, by+38)

        draw_back_btn(screen)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  SKINS SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def run_skins():
    sel = SKIN_ORDER.index(save.get("equipped","default"))
    COLS, ROWS = 3, 2
    cell_w, cell_h = 140, 150
    start_x = (W - COLS*cell_w)//2
    start_y = 130

    while True:
        dt = clock.tick(60)/1000
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:  sel = (sel-1)%len(SKIN_ORDER)
                if e.key == pygame.K_RIGHT: sel = (sel+1)%len(SKIN_ORDER)
                if e.key == pygame.K_UP:    sel = (sel-COLS)%len(SKIN_ORDER)
                if e.key == pygame.K_DOWN:  sel = (sel+COLS)%len(SKIN_ORDER)
                if e.key == pygame.K_RETURN:
                    sid = SKIN_ORDER[sel]
                    if sid in save.get("unlocked_skins",["default"]):
                        save["equipped"] = sid; write_save(save)
            if e.type == pygame.MOUSEBUTTONDOWN:
                for i, sid in enumerate(SKIN_ORDER):
                    col_i = i % COLS; row_i = i // COLS
                    cx = start_x + col_i*cell_w + cell_w//2
                    cy = start_y + row_i*cell_h + 40
                    if math.hypot(e.pos[0]-cx, e.pos[1]-cy) < 30: sel = i
                    # double-click equip handled by second click on selected
                sid2 = SKIN_ORDER[sel]
                if sid2 in save.get("unlocked_skins",["default"]):
                    save["equipped"] = sid2; write_save(save)
        if back_clicked(events): return

        screen.fill(BG)
        tc(screen, "SKINS", F_TITLE, WHITE, W//2, 52)
        tc(screen, "Click to equip  •  🔒 = locked", F_XSM, MID, W//2, 102)

        unlocked = save.get("unlocked_skins", ["default"])

        for i, sid in enumerate(SKIN_ORDER):
            sk = SKINS[sid]
            col_i = i % COLS; row_i = i // COLS
            cx = start_x + col_i*cell_w + cell_w//2
            cy = start_y + row_i*cell_h + 40
            is_unlocked = sid in unlocked
            is_sel      = (i == sel)
            is_equipped  = (save.get("equipped","default") == sid)

            # cell bg
            cell_rect = pygame.Rect(start_x+col_i*cell_w+6,
                                    start_y+row_i*cell_h+4,
                                    cell_w-12, cell_h-8)
            bg_c = (35,35,35) if is_sel else (22,22,22)
            border_c = CYAN if is_equipped else (YEL if is_sel else DIM)
            pygame.draw.rect(screen, bg_c,    cell_rect, border_radius=12)
            pygame.draw.rect(screen, border_c, cell_rect, 2, border_radius=12)

            if is_unlocked:
                draw_bird(screen, cx, cy, -1, sk)
            else:
                # locked: grey silhouette + lock
                grey_skin = dict(body=(50,50,50),ring=(35,35,35),eye=(70,70,70),
                                 beak=(40,40,40),wing=(35,35,35))
                draw_bird(screen, cx, cy, -1, grey_skin)
                tc(screen, "🔒", F_MED, MID, cx, cy-12)

            # name
            name_c = WHITE if is_unlocked else DIM
            tc(screen, sk["name"], F_SUB, name_c, cx, cy+28)

            # unlock hint
            if not is_unlocked:
                tc(screen, sk["desc"], F_XSM, (80,80,80), cx, cy+46)

            if is_equipped and is_unlocked:
                tc(screen, "equipped", F_XSM, CYAN, cx, cy+46)

        draw_back_btn(screen)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  MENU
# ══════════════════════════════════════════════════════════════════════════════
def run_menu():
    selected = 0
    btn_rects = [
        pygame.Rect(W//2-160, 190, 320, 62),
        pygame.Rect(W//2-160, 268, 320, 62),
        pygame.Rect(W//2-160, 346, 320, 62),
        pygame.Rect(W//2-160, 424, 320, 62),
    ]
    labels   = ["📐  Measurement", "🐦  Flappy Tilt",
                "🪁  Plappy Constant", "🎨  Skins"]
    subtexts = ["Live angle & tilt gauge",
                "Tilt UP to flap  •  Easy / Normal / Hard",
                "Screen angle = bird height  •  Easy / Normal / Hard",
                f"Equipped: {SKINS[save.get('equipped','default')]['name']}  •  {len(save.get('unlocked_skins',['default']))}/{len(SKINS)} unlocked"]
    anim = 0.0

    while True:
        dt = clock.tick(60)/1000
        anim += dt

        # refresh skin subtext live
        subtexts[3] = f"Equipped: {SKINS[save.get('equipped','default')]['name']}  •  {len(save.get('unlocked_skins',['default']))}/{len(SKINS)} unlocked"

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: imu.stop(); pygame.quit(); sys.exit()
                if e.key == pygame.K_UP:   selected = (selected-1)%4
                if e.key == pygame.K_DOWN: selected = (selected+1)%4
                if e.key == pygame.K_RETURN: return selected
            if e.type == pygame.MOUSEMOTION:
                for i,r in enumerate(btn_rects):
                    if r.collidepoint(e.pos): selected = i
            if e.type == pygame.MOUSEBUTTONDOWN:
                for i,r in enumerate(btn_rects):
                    if r.collidepoint(e.pos): return i

        screen.fill(BG)
        g = int(180+60*math.sin(anim*2))
        tc(screen, "SCREEN TILT", F_TITLE, (0,g,min(255,g+60)), W//2, 68)
        tc(screen, "Choose a mode", F_SM, MID, W//2, 132)

        _, _, _, _, _, _, lid = sensor_data()
        s_col = GREEN if lid is not None else YEL
        s_txt = f"sensor ready  {lid:.0f}°" if lid else "open lid slightly to wake sensor"
        pygame.draw.rect(screen, DIM, (W//2-150, 152, 300, 26), border_radius=13)
        tc(screen, s_txt, F_SM, s_col, W//2, 158)

        for i,(rect,label,sub) in enumerate(zip(btn_rects,labels,subtexts)):
            active = (i==selected)
            bg_c = (30,30,30) if not active else (0,55,75)
            border = CYAN if active else DIM
            pygame.draw.rect(screen, bg_c,   rect, border_radius=14)
            pygame.draw.rect(screen, border, rect, 2, border_radius=14)
            tc(screen, label, F_MENU, WHITE if active else MID, W//2, rect.y+8)
            tc(screen, sub,   F_SUB,  CYAN  if active else DIM,  W//2, rect.y+36)

        tc(screen, "↑↓ or mouse  •  Enter to launch", F_XSM, DIM, W//2, 508)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  MEASUREMENT
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
        tc(screen, "LID / SCREEN ANGLE", F_SM, MID, W//2, 52)
        lid_str = f"{lid:.1f}°" if lid is not None else "---"
        lid_c   = col(abs(lid-90)) if lid else DIM
        tc(screen, lid_str, F_BIG, lid_c, W//2, 64)

        CX, CY, R = W//2, 310, 115
        draw_arc(screen, CX, CY, R, 0, 180, DIM, 3)
        for d in range(0,181,10):
            rad = math.radians(d)
            inner = R-(14 if d%30==0 else 6)
            pygame.draw.line(screen, DIM if d%30 else MID,
                (int(CX+inner*math.cos(rad)), int(CY-inner*math.sin(rad))),
                (int(CX+R*math.cos(rad)),     int(CY-R*math.sin(rad))), 1)
            if d%30==0:
                lb = F_SM.render(f"{d}°", True, MID)
                screen.blit(lb,(int(CX+(R-22)*math.cos(rad)-lb.get_width()//2),
                                int(CY-(R-22)*math.sin(rad)-lb.get_height()//2)))
        if lid is not None:
            sweep = max(0.,min(180.,lid))
            draw_arc(screen, CX, CY, R, 0, sweep, lid_c, 5)
            rad = math.radians(sweep)
            nx,ny = int(CX+(R-8)*math.cos(rad)), int(CY-(R-8)*math.sin(rad))
            pygame.draw.line(screen, lid_c, (CX,CY), (nx,ny), 5)
            pygame.draw.circle(screen, lid_c, (nx,ny), 9)
        pygame.draw.circle(screen, CYAN, (CX,CY), 6)

        tl(screen, "BODY TILT", F_SM, MID, 55, 370)
        tl(screen, f"{tilt:.1f}°", F_MED, col(tilt), 55, 386)
        tl(screen, "ROLL", F_SM, MID, 270, 370)
        tl(screen, f"{roll:+.1f}°", F_MED, col(roll), 270, 386)
        tc(screen, f"gyro  x{gx:+.2f}  y{gy:+.2f}  z{gz:+.2f}  °/s", F_MONO, DIM, W//2, 448)
        hint = "open/close lid to wake sensor" if lid is None else \
               ("lid closed" if lid<10 else f"{lid:.1f}° open")
        tc(screen, hint, F_SM, MID, W//2, 476)
        draw_back_btn(screen)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  SHARED GAME HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def make_game_state(diff_key):
    d = DIFFICULTIES[diff_key]
    return dict(
        bird_y=H//2, bird_vel=0.0, pipes=[], score=0, alive=True,
        started=False, flash=0.0, ground_scroll=0.0,
        pipe_speed=d["pipe_speed"], pipe_gap=d["pipe_gap"],
        gravity=d["gravity"], flap_vel=d["flap_vel"],
        sky_col={"Easy":SKY_EASY,"Normal":SKY_NORMAL,"Hard":SKY_HARD}[diff_key],
    )

def spawn_pipe(gs):
    gap_top = random.randint(100, GROUND_Y - gs["pipe_gap"] - 60)
    gs["pipes"].append([W+70, gap_top, gap_top+gs["pipe_gap"], False])

def diff_badge(surf, diff_key):
    d = DIFFICULTIES[diff_key]
    s = F_XSM.render(diff_key, True, d["color"])
    bx, by = W-10-s.get_width()-8, 10
    pygame.draw.rect(surf, (30,30,30), (bx-4,by-2,s.get_width()+8,s.get_height()+4), border_radius=6)
    surf.blit(s, (bx, by))

# ══════════════════════════════════════════════════════════════════════════════
#  FLAPPY TILT
# ══════════════════════════════════════════════════════════════════════════════
def run_game(diff_key):
    gs       = make_game_state(diff_key)
    hi_score = save.get("hi_scores",{}).get(diff_key.lower(),{}).get("flappy",0)
    clouds   = make_clouds(6)
    last_lid = None
    FLAP_THRESH = 4
    skin     = get_skin()

    spawn_pipe(gs)

    def do_flap():
        if not gs["alive"]: return
        gs["started"] = True
        gs["bird_vel"] = gs["flap_vel"]

    def reset():
        nonlocal last_lid, skin
        gs.update(make_game_state(diff_key))
        gs["pipes"].clear(); spawn_pipe(gs)
        last_lid = None; skin = get_skin()

    while True:
        dt = clock.tick(60)/1000
        gs["flash"] = max(0.0, gs["flash"] - dt*3)
        toast.update(dt)

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN and not gs["alive"]: reset()
                if e.key == pygame.K_SPACE:
                    if not gs["alive"]: reset()
                    else: do_flap()
        if back_clicked(events): return

        _, _, _, _, _, _, lid = sensor_data()
        if lid is not None:
            if last_lid is not None:
                if lid - last_lid >= FLAP_THRESH:
                    if not gs["alive"]: reset()
                    else: do_flap()
            last_lid = lid

        if gs["alive"] and gs["started"]:
            gs["bird_vel"] += gs["gravity"] * dt
            gs["bird_y"]   += gs["bird_vel"] * dt
            gs["ground_scroll"] = (gs["ground_scroll"] + gs["pipe_speed"]*dt) % 40
            for p in gs["pipes"]: p[0] -= gs["pipe_speed"]*dt
            for p in gs["pipes"]:
                if not p[3] and p[0]+70 < BIRD_X:
                    p[3] = True; gs["score"] += 1
                    if gs["score"] > hi_score: hi_score = gs["score"]
            gs["pipes"] = [p for p in gs["pipes"] if p[0] > -90]
            if gs["pipes"][-1][0] < W-240: spawn_pipe(gs)

            br = BIRD_R-3
            if gs["bird_y"]-br < 0 or gs["bird_y"]+br > GROUND_Y:
                gs["alive"] = False; gs["flash"] = 1.0
            for p in gs["pipes"]:
                if (p[0]-br < BIRD_X+br < p[0]+70+br) and \
                   (gs["bird_y"]-br < p[1] or gs["bird_y"]+br > p[2]):
                    gs["alive"] = False; gs["flash"] = 1.0

            if not gs["alive"]:
                # save hi score + check unlocks
                hs = save.get("hi_scores",{}); dk = diff_key.lower()
                if dk not in hs: hs[dk] = {}
                hs[dk]["flappy"] = max(hs[dk].get("flappy",0), gs["score"])
                save["hi_scores"] = hs; write_save(save)
                newly = check_unlock(gs["score"], "flappy", diff_key)
                for sid in newly: toast.add(sid)

        # draw
        screen.fill(gs["sky_col"])
        draw_clouds(screen, clouds)
        for p in gs["pipes"]: draw_pipe(screen, int(p[0]), p[1], p[2])
        draw_ground(screen)
        for i in range(-1, W//40+2):
            pygame.draw.rect(screen, GROUND2,
                (int(i*40-gs["ground_scroll"]), GROUND_Y+8, 20, 8))

        if gs["alive"] or int(time.time()*8)%2==0:
            draw_bird(screen, BIRD_X,
                      max(BIRD_R, min(GROUND_Y-BIRD_R, gs["bird_y"])),
                      gs["bird_vel"], skin)

        if gs["flash"] > 0:
            ov = pygame.Surface((W,H), pygame.SRCALPHA)
            ov.fill((255,255,255,int(gs["flash"]*180))); screen.blit(ov,(0,0))

        tc(screen, str(gs["score"]), F_SCORE, WHITE, W//2, 30)
        diff_badge(screen, diff_key)

        if not gs["started"] and gs["alive"]:
            ov = pygame.Surface((360,100), pygame.SRCALPHA)
            ov.fill((0,0,0,150)); screen.blit(ov,(W//2-180, H//2-100))
            tc(screen, "FLAPPY TILT",           F_TITLE, WHITE, W//2, H//2-96)
            tc(screen, "Tilt screen UP to flap", F_SM,   WHITE, W//2, H//2-44)
            tc(screen, "or press SPACE",          F_SM,   CYAN,  W//2, H//2-24)

        if not gs["alive"]:
            ov = pygame.Surface((300,210), pygame.SRCALPHA)
            ov.fill((0,0,0,170)); screen.blit(ov,(W//2-150, H//2-105))
            tc(screen, "GAME OVER",               F_TITLE, RED,   W//2, H//2-96)
            tc(screen, f"Score: {gs['score']}",   F_MED,   WHITE, W//2, H//2-24)
            tc(screen, f"Best:  {hi_score}",       F_MED,   YEL,   W//2, H//2+16)
            tc(screen, "Tilt / Space / Enter",     F_SM,    CYAN,  W//2, H//2+62)

        toast.draw(screen)
        draw_back_btn(screen)
        pygame.display.flip()

# ══════════════════════════════════════════════════════════════════════════════
#  PLAPPY CONSTANT
# ══════════════════════════════════════════════════════════════════════════════
def run_plappy_constant(diff_key):
    gs       = make_game_state(diff_key)
    hi_score = save.get("hi_scores",{}).get(diff_key.lower(),{}).get("plappy",0)
    clouds   = make_clouds(6)
    skin     = get_skin()
    lid_min = lid_max = None
    CALIB_RANGE = 40.0
    bird_y  = [H//2]

    spawn_pipe(gs)

    def reset():
        nonlocal lid_min, lid_max, skin
        gs.update(make_game_state(diff_key))
        gs["pipes"].clear(); spawn_pipe(gs)
        lid_min = lid_max = None
        bird_y[0] = H//2; skin = get_skin()

    while True:
        dt = clock.tick(60)/1000
        gs["flash"] = max(0.0, gs["flash"]-dt*3)
        toast.update(dt)

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT: imu.stop(); pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if not gs["alive"]: reset()
        if back_clicked(events): return

        _, _, _, _, _, _, lid = sensor_data()
        if lid is not None and gs["alive"]:
            if lid_min is None: lid_min = lid - CALIB_RANGE/2; lid_max = lid + CALIB_RANGE/2
            lid_min = min(lid_min, lid); lid_max = max(lid_max, lid)
            span = max(lid_max - lid_min, 10.0)
            t = max(0.0, min(1.0, (lid - lid_min) / span))
            target_y = GROUND_Y - 20 - t*(GROUND_Y-60)
            bird_y[0] += (target_y - bird_y[0]) * min(1.0, dt*18)
            if not gs["started"] and abs(target_y - bird_y[0]) < 80: gs["started"] = True

        if gs["alive"] and gs["started"]:
            gs["ground_scroll"] = (gs["ground_scroll"]+gs["pipe_speed"]*dt) % 40
            for p in gs["pipes"]: p[0] -= gs["pipe_speed"]*dt
            for p in gs["pipes"]:
                if not p[3] and p[0]+70 < BIRD_X:
                    p[3] = True; gs["score"] += 1
                    if gs["score"] > hi_score: hi_score = gs["score"]
            gs["pipes"] = [p for p in gs["pipes"] if p[0] > -90]
            if gs["pipes"][-1][0] < W-240: spawn_pipe(gs)

            br = BIRD_R-3; by = bird_y[0]
            if by-br < 0 or by+br > GROUND_Y: gs["alive"] = False; gs["flash"] = 1.0
            for p in gs["pipes"]:
                if (p[0]-br < BIRD_X+br < p[0]+70+br) and \
                   (by-br < p[1] or by+br > p[2]):
                    gs["alive"] = False; gs["flash"] = 1.0

            if not gs["alive"]:
                hs = save.get("hi_scores",{}); dk = diff_key.lower()
                if dk not in hs: hs[dk] = {}
                hs[dk]["plappy"] = max(hs[dk].get("plappy",0), gs["score"])
                save["hi_scores"] = hs; write_save(save)
                newly = check_unlock(gs["score"], "plappy", diff_key)
                for sid in newly: toast.add(sid)

        # draw
        screen.fill(gs["sky_col"])
        draw_clouds(screen, clouds)
        for p in gs["pipes"]: draw_pipe(screen, int(p[0]), p[1], p[2])
        draw_ground(screen)
        for i in range(-1, W//40+2):
            pygame.draw.rect(screen, GROUND2,
                (int(i*40-gs["ground_scroll"]), GROUND_Y+8, 20, 8))

        if gs["alive"] or int(time.time()*8)%2==0:
            draw_bird(screen, BIRD_X,
                      max(BIRD_R, min(GROUND_Y-BIRD_R, bird_y[0])), 0, skin)

        if gs["flash"] > 0:
            ov = pygame.Surface((W,H), pygame.SRCALPHA)
            ov.fill((255,255,255,int(gs["flash"]*180))); screen.blit(ov,(0,0))

        # lid bar
        if lid is not None and lid_min is not None:
            bh = GROUND_Y-30; bx = 18
            pygame.draw.rect(screen, DIM, (bx,15,10,bh), border_radius=5)
            span = max(lid_max-lid_min, 10.0)
            tf = max(0., min(1., (lid-lid_min)/span))
            fy = 15+bh-int(tf*bh)
            pygame.draw.rect(screen, CYAN, (bx,fy,10,15+bh-fy), border_radius=5)
            tl(screen, f"{lid:.0f}°", F_XSM, CYAN, 6, fy-15)

        tc(screen, str(gs["score"]), F_SCORE, WHITE, W//2, 30)
        diff_badge(screen, diff_key)

        if not gs["started"] and gs["alive"]:
            ov = pygame.Surface((360,100), pygame.SRCALPHA)
            ov.fill((0,0,0,150)); screen.blit(ov,(W//2-180, H//2-100))
            tc(screen, "PLAPPY CONSTANT",           F_TITLE, WHITE, W//2, H//2-96)
            tc(screen, "Screen angle = bird height", F_SM,   WHITE, W//2, H//2-44)
            tc(screen, "Tilt to move — auto-starts", F_SM,   CYAN,  W//2, H//2-24)

        if not gs["alive"]:
            ov = pygame.Surface((300,210), pygame.SRCALPHA)
            ov.fill((0,0,0,170)); screen.blit(ov,(W//2-150, H//2-105))
            tc(screen, "GAME OVER",               F_TITLE, RED,   W//2, H//2-96)
            tc(screen, f"Score: {gs['score']}",   F_MED,   WHITE, W//2, H//2-24)
            tc(screen, f"Best:  {hi_score}",       F_MED,   YEL,   W//2, H//2+16)
            tc(screen, "Enter / Space to restart", F_SM,    CYAN,  W//2, H//2+62)

        toast.draw(screen)
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
        diff = pick_difficulty("🐦  Flappy Tilt")
        if diff: run_game(diff)
    elif choice == 2:
        diff = pick_difficulty("🪁  Plappy Constant")
        if diff: run_plappy_constant(diff)
    elif choice == 3:
        run_skins()
