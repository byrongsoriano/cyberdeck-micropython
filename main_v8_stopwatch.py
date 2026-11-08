from machine import Pin, SPI, PWM
import framebuf
import time
import random
import math
import gc
from micropython import const
from array import array
TFT_SCK = const(18)
TFT_MOSI = const(19)
TFT_CS = const(17)
TFT_DC = const(16)
TFT_RST = const(20)
BTN_NAV = const(14)
BTN_SELECT = const(12)
BUZZER_PIN = const(22)
BUZZER_ACTIVE_LOW = True
TFT_BGR = False
TFT_X_OFFSET = const(0)
TFT_Y_OFFSET = const(0)
class ST7735:
    W = 160
    H = 128
    def __init__(self, spi, cs, dc, rst, buf):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.buf = buf
        self.fb = framebuf.FrameBuffer(self.buf, self.W, self.H, framebuf.RGB565)
        self._reset()
        self._init()
    def _cmd(self, c, data=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([c]))
        if data:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)
    def _reset(self):
        self.cs(1)
        self.rst(1)
        time.sleep_ms(5)
        self.rst(0)
        time.sleep_ms(20)
        self.rst(1)
        time.sleep_ms(150)
    def _init(self):
        madctl = 0xA0 | (0x08 if TFT_BGR else 0x00)
        seq = (
            (0x01, None, 150),
            (0x11, None, 500),
            (0xB1, b'\x01\x2c\x2d', 0),
            (0xB2, b'\x01\x2c\x2d', 0),
            (0xB3, b'\x01\x2c\x2d\x01\x2c\x2d', 0),
            (0xB4, b'\x07', 0),
            (0xC0, b'\xa2\x02\x84', 0),
            (0xC1, b'\xc5', 0),
            (0xC2, b'\x0a\x00', 0),
            (0xC3, b'\x8a\x2a', 0),
            (0xC4, b'\x8a\xee', 0),
            (0xC5, b'\x0e', 0),
            (0x20, None, 0),
            (0x36, bytes([madctl]), 0),
            (0x3A, b'\x05', 0),
            (0xE0, b'\x02\x1c\x07\x12\x37\x32\x29\x2d\x29\x25\x2b\x39\x00\x01\x03\x10', 0),
            (0xE1, b'\x03\x1d\x07\x06\x2e\x2c\x29\x2d\x2e\x2e\x37\x3f\x00\x00\x02\x10', 0),
            (0x13, None, 10),
            (0x29, None, 100),
        )
        for cmd, data, delay in seq:
            self._cmd(cmd, data)
            if delay:
                time.sleep_ms(delay)
        x0, y0 = TFT_X_OFFSET, TFT_Y_OFFSET
        self._cmd(0x2A, bytes([0, x0, 0, x0 + self.W - 1]))
        self._cmd(0x2B, bytes([0, y0, 0, y0 + self.H - 1]))
    def show(self):
        self._cmd(0x2C, self.buf)
HISCORE = {}
def pressed(btn): return btn.value() == 0
def wait_release(btn):
    while pressed(btn): time.sleep_ms(10)
def rand(a, b): return random.randint(a, b - 1)
def update_best(key, score):
    best = max(HISCORE.get(key, 0), score)
    HISCORE[key] = best
    return best
def rgb(r, g, b):
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)
def mix(a, b, t):
    return rgb(int(a[0] + (b[0] - a[0]) * t),
               int(a[1] + (b[1] - a[1]) * t),
               int(a[2] + (b[2] - a[2]) * t))
C_BLACK      = const(0x0000)
C_NAVY       = rgb(8, 12, 28)
C_DARK_GREY  = rgb(30, 35, 45)
C_GREY       = rgb(70, 75, 90)
C_WHITE      = const(0xFFFF)
C_CYAN       = rgb(0, 240, 255)
C_CYAN_DIM   = rgb(0, 90, 110)
C_NEON_PINK  = rgb(255, 0, 128)
C_PINK_DIM   = rgb(80, 0, 40)
C_PINKISH    = rgb(255, 150, 190)
C_GREEN      = rgb(0, 255, 100)
C_DARK_GREEN = rgb(0, 140, 50)
C_YELLOW     = rgb(255, 220, 0)
C_YEL_DIM    = rgb(70, 60, 0)
C_LIGHT_YEL  = rgb(255, 245, 170)
C_ORANGE     = rgb(255, 120, 0)
C_RED        = rgb(255, 40, 40)
C_BLUE       = rgb(30, 100, 255)
C_PURPLE     = rgb(160, 32, 240)
C_ITEM       = rgb(28, 26, 52)
C_KEY        = const(0xF81F)  # Magic pink for transparency key
HDR = array('H', (mix((45, 50, 80), (14, 16, 30), i / 13) for i in range(14)))
FTR = array('H', (mix((14, 16, 30), (40, 45, 70), i / 13) for i in range(14)))
SEL_GRAD = array('H', (mix((255, 0, 128), (120, 0, 170), i / 14) for i in range(15)))
PULSE = array('H', (mix((0, 240, 255), (255, 255, 255), t) for t in (0, 0.25, 0.5, 0.75, 1, 0.75, 0.5, 0.25)))
SIN = array('b', (int(8 * math.sin(i * 2 * math.pi / 32)) for i in range(32)))
gc.collect() # Collect garbage after palette generation
def sprite(rows, pal):
    h = len(rows)
    w = max(len(r) for r in rows)
    s = framebuf.FrameBuffer(bytearray(w * h * 2), w, h, framebuf.RGB565)
    s.fill(C_KEY)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '.':
                s.pixel(x, y, pal[ch])
    return s
def flip(rows):
    return tuple(''.join(list(reversed(r))) for r in rows)
BIRD_PAL = {'K': C_BLACK, 'Y': C_YELLOW, 'y': rgb(230, 160, 0),
            'w': rgb(255, 250, 200), 'W': C_WHITE, 'O': C_ORANGE}
_BIRD_TOP = ("....KKKK....", "...KYYYYWK..", "..KYYYYWKWK.")
BIRD_UP = sprite(_BIRD_TOP + (".KwwwKYYWWWK", "KwwwwKYYKKKK", "KwwwKYYKOOOO", ".KKKyyyyKKK.", "..KyyyyyyK..", "...KKKKKK..."), BIRD_PAL)
BIRD_DN = sprite(_BIRD_TOP + (".KKKKYYYWWWK", "KYYYYYYYKKKK", "KwwwwKYKOOOO", ".KwwwKyyKKK.", "..KKKyyyyK..", "...KKKKKK..."), BIRD_PAL)
SHIP = sprite((".....W.....", "....WCW....", "....CCC....", "...CCBCC...", ".b.CBBBC.b.", "bbCCBBBCCbb", "bBBBBBBBBBb", "bb.......bb"), {'W': C_WHITE, 'C': C_CYAN, 'B': C_BLUE, 'b': rgb(10, 40, 140)})
_ALIEN_A = ("..P......P..", "...P....P...", "..PPPPPPPP..", ".PPYPPPPYPP.", "PPPPPPPPPPPP", "P.PPPPPPPP.P", "P.P......P.P", "...PP..PP...")
_ALIEN_B = ("..P......P..", "P..P....P..P", "P.PPPPPPPP.P", "PPPYPPPPYPPP", "PPPPPPPPPPPP", ".PPPPPPPPPP.", "..P......P..", ".P........P.")
ALIEN_SPR = [(sprite(_ALIEN_A, {'P': c, 'Y': C_YELLOW}), sprite(_ALIEN_B, {'P': c, 'Y': C_YELLOW})) for c in (C_NEON_PINK, C_PURPLE, C_GREEN, C_ORANGE, C_CYAN)]
ICON_PAL = {'K': C_BLACK, 'Y': C_YELLOW, 'y': rgb(230, 160, 0), 'w': rgb(255, 250, 200), 'W': C_WHITE, 'O': C_ORANGE, 'P': C_NEON_PINK, 'G': C_GREEN, 'g': C_DARK_GREEN}
ICONS = [sprite(r, ICON_PAL) for r in (
    ("..KKKK..", ".KYYWKK.", "KwwYYYOO", "KwwwYYOO", ".KYYYYK.", "..KyyK..", "...KK...", "........"),
    (".P....P.", "..P..P..", ".PPPPPP.", "PPYPPYPP", "PPPPPPPP", "P.PPPP.P", "P.P..P.P", ".PP..PP."),
    ("..WWWW..", ".WKKKKW.", ".WYYYYW.", ".WWWWWW.", ".WPKPWK.", ".WPKPWK.", ".WWWWWW.", "........"),
    ("..WWWW..", ".W....W.", "W..WW..W", "W..WW..W", "W......W", "W......W", ".W....W.", "..WWWW.."),
)]
gc.collect()
def vgrad(surf, x, y, w, h, a, b):
    for i in range(h): surf.hline(x, y + i, w, mix(a, b, i / (h - 1) if h > 1 else 0))
def fill_round(surf, x, y, w, h, c):
    surf.fill_rect(x + 1, y, w - 2, h, c)
    surf.fill_rect(x, y + 1, w, h - 2, c)
def round_rect(surf, x, y, w, h, c):
    surf.hline(x + 1, y, w - 2, c)
    surf.hline(x + 1, y + h - 1, w - 2, c)
    surf.vline(x, y + 1, h - 2, c)
    surf.vline(x + w - 1, y + 1, h - 2, c)
def text_shadow(s, x, y, c, sh=C_BLACK):
    fb.text(s, x + 1, y + 1, sh)
    fb.text(s, x, y, c)
def text_bold(s, x, y, c, sh=C_BLACK):
    fb.text(s, x + 1, y + 1, sh)
    fb.text(s, x + 2, y + 1, sh)
    fb.text(s, x, y, c)
    fb.text(s, x + 1, y, c)
def center_x(s, sc=1): return (160 - len(s) * 8 * sc) // 2
def text_big(s, x, y, c, sc=2):
    w = len(s) * 8
    m = framebuf.FrameBuffer(bytearray(w * 8), w, 8, framebuf.MONO_HLSB)
    m.fill(0)
    m.text(s, 0, 0, 1)
    for yy in range(8):
        for xx in range(w):
            if m.pixel(xx, yy):
                fb.fill_rect(x + xx * sc, y + yy * sc, sc, sc, c)
def draw_header(title, right=None, accent=C_CYAN):
    for i in range(14): fb.hline(0, i, 160, HDR[i])
    fb.hline(0, 14, 160, accent)
    fb.hline(0, 15, 160, C_CYAN_DIM)
    fb.fill_rect(3, 3, 2, 8, C_NEON_PINK)
    text_shadow(title, 8, 3, accent)
    if right is not None:
        s = str(right)
        text_shadow(s, 156 - 8 * len(s), 3, C_YELLOW)
def draw_footer(nav="NAV", sel="SELECT"):
    fb.hline(0, 113, 160, C_CYAN_DIM)
    for i in range(14): fb.hline(0, 114 + i, 160, FTR[i])
    w1 = len(nav) * 8 + 8
    fill_round(fb, 3, 116, w1, 11, C_YEL_DIM)
    fb.text(nav, 7, 118, C_YELLOW)
    w2 = len(sel) * 8 + 8
    fill_round(fb, 157 - w2, 116, w2, 11, C_PINK_DIM)
    fb.text(sel, 161 - w2, 118, C_NEON_PINK)
def panel(x, y, w, h, border):
    fb.fill_rect(x + 3, y + 3, w, h, C_BLACK)
    vgrad(fb, x, y, w, h, (45, 50, 75), (15, 18, 32))
    fb.rect(x, y, w, h, border)
    fb.rect(x + 2, y + 2, w - 4, h - 4, C_GREY)
def dim_screen():
    for y in range(16, 113, 2): fb.hline(0, y, 160, C_BLACK)
def game_over_panel(title, col, score, best):
    dim_screen()
    panel(14, 32, 132, 62, col)
    text_bold(title, center_x(title), 39, col)
    fb.hline(24, 51, 112, C_GREY)
    s, b = str(score), str(best)
    text_shadow("SCORE", 28, 57, C_WHITE)
    text_shadow(s, 132 - 8 * len(s), 57, C_YELLOW)
    text_shadow("BEST", 28, 67, C_WHITE)
    text_shadow(b, 132 - 8 * len(b), 67, C_CYAN)
    fb.text("NAV: RESTART", center_x("NAV: RESTART"), 80, C_GREY)
    tft.show()
def tone(freq, ms):
    pwm = PWM(Pin(BUZZER_PIN))
    pwm.freq(freq)
    pwm.duty_u16(32768)
    time.sleep_ms(ms)
    pwm.deinit()
    Pin(BUZZER_PIN, Pin.OUT, value=BUZZER_IDLE)
def snd_nav(): tone(1200, 15)
def snd_select(): tone(1800, 30); tone(2400, 40)
def snd_jump(): tone(800, 20); tone(1400, 30)
def snd_score(): tone(1000, 30); time.sleep_ms(5); tone(2000, 50)
def snd_game_over(): tone(600, 100); tone(400, 100); tone(200, 200)
def snd_bubble(): tone(1500, 10); time.sleep_ms(5); tone(2200, 15)
def snd_glitch():
    if rand(0, 5) == 0: tone(rand(2000, 4000), 5)
def snd_laser(): tone(2200, 10); tone(1200, 15)
def snd_hit(): tone(300, 20); tone(800, 30)
def snd_alien_tick(): tone(150, 10)
def enter_app():
    wait_release(btn_sel)
    time.sleep_ms(100)
    fb.fill(C_BLACK)
    tft.show()
    gc.collect()
def exit_app():
    snd_select()
    time.sleep_ms(200)
    wait_release(btn_sel)
    gc.collect()
P_EDGE = rgb(20, 70, 20)
P_DARK = rgb(40, 140, 40)
P_MID = rgb(80, 200, 60)
P_LIGHT = rgb(150, 240, 110)
P_HI = rgb(220, 255, 190)
G_GRASS = rgb(90, 220, 70)
G_GRASS_D = rgb(40, 150, 40)
G_DIRT = rgb(170, 110, 55)
G_DIRT_D = rgb(130, 80, 40)
def draw_pipe(x, y, h, cap_bottom):
    fb.fill_rect(x, y, 18, h, P_MID)
    fb.fill_rect(x + 2, y, 4, h, P_LIGHT)
    fb.vline(x + 3, y, h, P_HI)
    fb.fill_rect(x + 13, y, 5, h, P_DARK)
    fb.vline(x, y, h, P_EDGE)
    fb.vline(x + 17, y, h, P_EDGE)
    cy = y + h - 6 if cap_bottom else y
    fb.fill_rect(x - 2, cy, 22, 6, P_MID)
    fb.fill_rect(x, cy, 4, 6, P_LIGHT)
    fb.fill_rect(x + 14, cy, 5, 6, P_DARK)
    fb.rect(x - 2, cy, 22, 6, P_EDGE)
def draw_ground(off):
    fb.fill_rect(0, 110, 160, 18, G_DIRT)
    fb.fill_rect(0, 110, 160, 4, G_GRASS_D)
    s = off % 8
    for x in range(-s, 160, 8):
        fb.fill_rect(x, 110, 4, 4, G_GRASS)
        fb.fill_rect(x + 2, 119, 3, 2, G_DIRT_D)
        fb.fill_rect(x + 6, 124, 2, 2, G_DIRT_D)
def bake_flappy_bg():
    vgrad(bg, 0, 0, 160, 110, (20, 12, 60), (255, 120, 80))
    for _ in range(25): bg.pixel(rand(0, 160), rand(16, 50), C_WHITE)
    bg.ellipse(118, 72, 15, 15, rgb(255, 200, 110), True)
    bg.ellipse(118, 72, 11, 11, rgb(255, 230, 160), True)
    for cx, cy in ((30, 34), (95, 26), (140, 44)):
        bg.ellipse(cx, cy, 10, 3, rgb(255, 170, 160), True)
        bg.ellipse(cx + 5, cy - 2, 6, 3, rgb(255, 200, 185), True)
    far, near, win = rgb(110, 55, 120), rgb(55, 25, 75), rgb(255, 200, 90)
    x = 0
    while x < 160:
        w, h = rand(10, 20), rand(14, 34)
        bg.fill_rect(x, 110 - h, w, h, far)
        x += w + rand(0, 4)
    x = 0
    while x < 160:
        w, h = rand(8, 16), rand(8, 22)
        bg.fill_rect(x, 110 - h, w, h, near)
        for wy in range(110 - h + 3, 108, 4):
            for wx in range(x + 2, x + w - 2, 3):
                if rand(0, 3) == 0: bg.pixel(wx, wy, win)
        x += w + rand(1, 5)
def run_flappy_bird():
    enter_app()
    bake_flappy_bg()
    bird_y = 50.0
    velocity = 0.0
    gravity = 0.35
    pipe_x = 160
    pipe_gap_y = 40
    gap_height = 36
    score = 0
    game_over = False
    nav_held = False
    shown = False
    sky_off = 0
    ground_off = 0
    tick = 0
    while True:
        if pressed(btn_sel):
            exit_app()
            return
        if not game_over:
            if pressed(btn_nav):
                if not nav_held:
                    velocity = -2.2
                    snd_jump()
                    nav_held = True
            else:
                nav_held = False
            velocity += gravity
            bird_y += velocity
            if bird_y < 16: bird_y = 16
            if bird_y > 102:
                bird_y = 102
                game_over = True
                snd_game_over()
            pipe_x -= 3
            if pipe_x < -20:
                pipe_x = 160
                pipe_gap_y = rand(20, 65)
                score += 1
                snd_score()
            if pipe_x < 30 and pipe_x + 18 > 20:
                if bird_y < pipe_gap_y or (bird_y + 8) > (pipe_gap_y + gap_height):
                    game_over = True
                    snd_game_over()
            sky_off = (sky_off + 1) % 160
            ground_off += 3
            tick += 1
            fb.blit(bg, -sky_off, 0)
            fb.blit(bg, 160 - sky_off, 0)
            top_h = pipe_gap_y - 15
            bot_y = pipe_gap_y + gap_height
            bot_h = 110 - bot_y
            if top_h > 0: draw_pipe(pipe_x, 15, top_h, True)
            if bot_h > 0: draw_pipe(pipe_x, bot_y, bot_h, False)
            draw_ground(ground_off)
            frame = BIRD_DN if velocity < 0 or (tick // 4) % 2 else BIRD_UP
            fb.blit(frame, 19, int(bird_y), C_KEY)
            draw_header("FLAPPY BIRD", score)
            tft.show()
            time.sleep_ms(30)
        else:
            if not shown:
                game_over_panel("GAME OVER", C_RED, score, update_best("flappy", score))
                shown = True
            if pressed(btn_nav):
                snd_nav()
                bird_y = 50.0
                velocity = 0.0
                pipe_x = 160
                score = 0
                game_over = False
                shown = False
                nav_held = True
            time.sleep_ms(20)
def bake_invaders_bg():
    vgrad(bg, 0, 0, 160, 128, (0, 0, 8), (35, 5, 55))
    bg.ellipse(40, 50, 30, 14, rgb(45, 12, 70), True)
    bg.ellipse(55, 58, 18, 8, rgb(70, 20, 95), True)
    bg.ellipse(110, 85, 26, 10, rgb(15, 25, 70), True)
    bg.ellipse(100, 82, 12, 5, rgb(25, 40, 95), True)
    for _ in range(40):
        v = rand(50, 140)
        bg.pixel(rand(0, 160), rand(16, 108), rgb(v, v, v + 30))
    bg.ellipse(138, 32, 9, 9, rgb(200, 100, 50), True)
    bg.ellipse(140, 30, 6, 6, rgb(240, 150, 80), True)
    bg.pixel(142, 27, rgb(255, 220, 170))
    bg.ellipse(138, 32, 15, 3, rgb(255, 210, 150))
    bg.hline(0, 109, 160, rgb(0, 200, 130))
    bg.fill_rect(0, 110, 160, 3, rgb(0, 60, 40))
def run_space_invaders():
    enter_app()
    bake_invaders_bg()
    def fresh():
        return 75, 2, False, -1, -1, [True] * 5, [15, 45, 75, 105, 135], 25, 2, 0, 0, False, False, [[rand(0, 160), rand(16, 108), rand(1, 3)] for _ in range(14)]
    (player_x, player_dir, bullet_active, bullet_x, bullet_y, aliens, alien_x,
     alien_y, alien_dir, alien_step, score, game_over, victory, stars) = fresh()
    alien_frame = 0
    parts = []
    tick = 0
    shown = False
    while True:
        if pressed(btn_sel):
            exit_app()
            return
        if not game_over and not victory:
            tick += 1
            player_x += player_dir
            if player_x >= 145: player_x = 145; player_dir = -2
            if player_x <= 5: player_x = 5; player_dir = 2
            if pressed(btn_nav) and not bullet_active:
                bullet_active = True
                bullet_x = player_x + 5
                bullet_y = 98
                snd_laser()
            if bullet_active:
                bullet_y -= 4
                if bullet_y < 15: bullet_active = False
            alien_step += 1
            if alien_step >= 6:
                alien_step = 0
                alien_frame ^= 1
                snd_alien_tick()
                hit_edge = False
                for i in range(5):
                    if aliens[i]:
                        alien_x[i] += alien_dir
                        if alien_x[i] >= 145 or alien_x[i] <= 5: hit_edge = True
                if hit_edge:
                    alien_dir = -alien_dir
                    alien_y += 4
            if bullet_active:
                for i in range(5):
                    if aliens[i] and (alien_x[i] <= bullet_x <= alien_x[i] + 12) and (alien_y <= bullet_y <= alien_y + 8):
                        aliens[i] = False
                        bullet_active = False
                        score += 10
                        snd_hit()
                        for _ in range(12):
                            parts.append([alien_x[i] + 6, alien_y + 4, rand(-20, 21) / 10, rand(-20, 21) / 10, rand(6, 12)])
                        break
            if not any(aliens):
                victory = True
                snd_score()
            if alien_y >= 90:
                game_over = True
                snd_game_over()
            fb.blit(bg, 0, 0)
            for s in stars:
                s[1] += s[2]
                if s[1] > 107:
                    s[1] = 16
                    s[0] = rand(0, 160)
                fb.pixel(s[0], s[1], C_WHITE if s[2] > 1 else C_GREY)
            px = int(player_x)
            fb.blit(SHIP, px, 100, C_KEY)
            fb.fill_rect(px + 4, 108, 3, 1, C_ORANGE if tick % 2 else C_YELLOW)
            if tick % 3: fb.pixel(px + 5, 109, C_RED)
            if bullet_active:
                fb.vline(bullet_x - 1, bullet_y + 1, 4, C_PINK_DIM)
                fb.vline(bullet_x + 1, bullet_y + 1, 4, C_PINK_DIM)
                fb.vline(bullet_x, bullet_y, 6, C_NEON_PINK)
                fb.pixel(bullet_x, bullet_y, C_WHITE)
            for i in range(5):
                if aliens[i]:
                    fb.blit(ALIEN_SPR[i][alien_frame], alien_x[i], alien_y, C_KEY)
            alive = []
            for p in parts:
                p[0] += p[2]
                p[1] += p[3]
                p[4] -= 1
                if p[4] > 0:
                    col = C_YELLOW if p[4] > 7 else (C_ORANGE if p[4] > 3 else C_RED)
                    fb.fill_rect(int(p[0]), int(p[1]), 2, 2, col)
                    alive.append(p)
            parts = alive
            draw_header("INVADERS", score)
            draw_footer("FIRE", "EXIT")
            tft.show()
            time.sleep_ms(40)
        else:
            if not shown:
                game_over_panel("VICTORY!" if victory else "GAME OVER", C_GREEN if victory else C_RED, score, update_best("invaders", score))
                shown = True
            if pressed(btn_nav):
                snd_nav()
                (player_x, player_dir, bullet_active, bullet_x, bullet_y, aliens, alien_x,
                 alien_y, alien_dir, alien_step, score, game_over, victory, stars) = fresh()
                parts = []
                shown = False
            time.sleep_ms(20)
def run_calculator():
    enter_app()
    keys = [
        'C', 'DEL', '^', '/',
        '7', '8', '9', '*',
        '4', '5', '6', '-',
        '1', '2', '3', '+',
        'EXIT', '0', '.', '='
    ]
    cursor = 0
    expr = ""
    result = ""
    vgrad(bg, 0, 0, 160, 128, (20, 25, 40), (5, 10, 20))
    cols, rows = 4, 5
    kw, kh = 32, 14
    pad_x, pad_y = 4, 3
    start_x = 10
    start_y = 40
    last_nav = time.ticks_ms()
    last_sel = last_nav
    debounce = 150
    while True:
        now = time.ticks_ms()
        if pressed(btn_nav) and time.ticks_diff(now, last_nav) > debounce:
            snd_nav()
            cursor = (cursor + 1) % len(keys)
            last_nav = now
        if pressed(btn_sel) and time.ticks_diff(now, last_sel) > debounce:
            snd_select()
            k = keys[cursor]
            if k == 'EXIT':
                exit_app()
                return
            elif k == 'C':
                expr = ""
                result = ""
            elif k == 'DEL':
                expr = expr[:-1]
                result = ""
            elif k == '=':
                try:
                    safe_expr = expr.replace('^', '**')
                    res = eval(safe_expr)
                    if isinstance(res, float):
                        result = "{:.4g}".format(res)
                    else:
                        result = str(res)
                except Exception:
                    result = "Err"
            else:
                if len(expr) < 16:
                    expr += k
            last_sel = now
        fb.blit(bg, 0, 0)
        draw_header("CALC", accent=C_CYAN)
        panel(10, 16, 140, 20, C_CYAN_DIM)
        if result:
            fb.text(expr, 14, 22, C_GREY)
            res_str = "=" + result
            fb.text(res_str, 146 - len(res_str)*8, 22, C_GREEN)
        else:
            fb.text(expr + "_", 14, 22, C_WHITE)
        for i, k in enumerate(keys):
            c = i % cols
            r = i // cols
            kx = start_x + c * (kw + pad_x)
            ky = start_y + r * (kh + pad_y)
            if i == cursor:
                fill_round(fb, kx, ky, kw, kh, C_CYAN)
                fb.text(k, kx + (kw - len(k)*8)//2, ky + 3, C_BLACK)
            else:
                fill_round(fb, kx, ky, kw, kh, C_ITEM)
                col = C_RED if k == 'EXIT' else (C_ORANGE if k in "C DEL = ^ / * - +" else C_WHITE)
                fb.text(k, kx + (kw - len(k)*8)//2, ky + 3, col)
        tft.show()
        time.sleep_ms(30)

def run_stopwatch():
    enter_app()
    start_ticks = 0
    elapsed = 0
    running = False
    last_nav = time.ticks_ms()
    debounce = 150
    while True:
        now = time.ticks_ms()
        if pressed(btn_sel):
            exit_app()
            return
        if pressed(btn_nav) and time.ticks_diff(now, last_nav) > debounce:
            snd_nav()
            if not running:
                if start_ticks == 0 and elapsed == 0:
                    start_ticks = now
                elif elapsed > 0:
                    elapsed = 0
                    start_ticks = 0
                running = True
            else:
                running = False
                elapsed += time.ticks_diff(now, start_ticks)
            last_nav = now
        fb.fill(C_BLACK)
        draw_header("STOPWATCH", accent=C_ORANGE)
        panel(10, 30, 140, 50, C_CYAN_DIM)
        current_time = elapsed
        if running:
            current_time += time.ticks_diff(now, start_ticks)
        mins = current_time // 60000
        secs = (current_time % 60000) // 1000
        ms = (current_time % 1000) // 10
        time_str = "{:02d}:{:02d}.{:02d}".format(mins, secs, ms)
        text_big(time_str, 24, 46, C_WHITE, 2)
        if running:
            fb.text("NAV: STOP", center_x("NAV: STOP"), 95, C_RED)
        elif elapsed > 0:
            fb.text("NAV: RESET", center_x("NAV: RESET"), 95, C_YELLOW)
        else:
            fb.text("NAV: START", center_x("NAV: START"), 95, C_GREEN)
        tft.show()
        time.sleep_ms(30)

APP_NAMES = ("Flappy Bird", "Space Invaders", "Calculator", "Stopwatch")
APPS = (run_flappy_bird, run_space_invaders, run_calculator, run_stopwatch)
def bake_menu_bg():
    vgrad(bg, 0, 0, 160, 128, (12, 6, 34), (45, 12, 70))
    for _ in range(35):
        v = rand(60, 160)
        bg.pixel(rand(0, 160), rand(16, 113), rgb(v, v, v + 40))
def render_menu(current, phase):
    fb.blit(bg, 0, 0)
    for i, name in enumerate(APP_NAMES):
        y = 19 + i * 19
        if i == current:
            for r in range(15):
                if r == 0 or r == 14: fb.hline(11, y + r, 138, SEL_GRAD[r])
                else: fb.hline(10, y + r, 140, SEL_GRAD[r])
            round_rect(fb, 9, y - 1, 142, 17, PULSE[phase % len(PULSE)])
            iy = y + 3 - (1 if phase % 4 < 2 else 0)
            fb.blit(ICONS[i], 15, iy, C_KEY)
            text_shadow(name, 30, y + 4, C_WHITE)
            fb.text(">", phase % 2, y + 4, C_CYAN)
        else:
            fill_round(fb, 10, y, 140, 15, C_ITEM)
            fb.vline(10, y + 2, 11, C_CYAN_DIM)
            fb.blit(ICONS[i], 15, y + 3, C_KEY)
            fb.text(name, 30, y + 4, C_CYAN)
    draw_header("CYBERDECK V3.1")
    draw_footer("NEXT", "LAUNCH")
    tft.show()
def splash():
    fb.fill(C_BLACK)
    tft.show()
    tone(1000, 50); time.sleep_ms(10); tone(1500, 50); time.sleep_ms(10); tone(2000, 80)
    vgrad(fb, 0, 0, 160, 82, (8, 0, 26), (110, 15, 90))
    for _ in range(30): fb.pixel(rand(0, 160), rand(0, 48), C_WHITE)
    for y in range(52, 82):
        if y > 66 and y % 4 == 0: continue
        dy = 82 - y
        half = int(math.sqrt(900 - dy * dy))
        fb.hline(80 - half, y, 2 * half, mix((255, 230, 60), (255, 0, 130), (y - 52) / 30))
    fb.fill_rect(0, 82, 160, 46, rgb(16, 0, 30))
    grid = rgb(200, 0, 150)
    for i in range(-9, 10): fb.line(80 + i * 9, 82, 80 + i * 48, 127, grid)
    for y in (84, 87, 91, 96, 102, 109, 117, 126): fb.hline(0, y, 160, grid)
    fb.hline(0, 82, 160, C_NEON_PINK)
    text_big("CYBERDECK", 9, 15, C_NEON_PINK)
    text_big("CYBERDECK", 8, 14, C_CYAN)
    sub = "OS v3.1  PICO 2"
    text_shadow(sub, center_x(sub), 37, C_YELLOW)
    tft.show()
    fill_round(fb, 28, 106, 104, 10, C_BLACK)
    round_rect(fb, 28, 106, 104, 10, C_CYAN)
    for i in range(0, 100, 4):
        fb.fill_rect(30 + i, 108, 4, 6, mix((0, 240, 255), (255, 0, 128), i / 100))
        tft.show()
        time.sleep_ms(15)
    time.sleep_ms(400)
    gc.collect()
def main():
    gc.collect()
    splash()
    bake_menu_bg()
    current = 0
    phase = 0
    last = time.ticks_ms()
    last_anim = last
    debounce = 150
    render_menu(current, phase)
    while True:
        now = time.ticks_ms()
        if pressed(btn_nav) and time.ticks_diff(now, last) > debounce:
            last = now
            snd_nav()
            current = (current + 1) % len(APPS)
            render_menu(current, phase)
        if pressed(btn_sel) and time.ticks_diff(now, last) > debounce:
            last = now
            snd_select()
            APPS[current]()
            bake_menu_bg()
            render_menu(current, phase)
            last = time.ticks_ms()
        if time.ticks_diff(now, last_anim) > 90:
            last_anim = now
            phase += 1
            render_menu(current, phase)
        time.sleep_ms(20)
gc.collect()
_tft_buf = bytearray(160 * 128 * 2)
_bg_buf = bytearray(160 * 128 * 2)
spi = SPI(0, baudrate=24_000_000, polarity=0, phase=0,
          sck=Pin(TFT_SCK), mosi=Pin(TFT_MOSI))
tft = ST7735(spi,
             cs=Pin(TFT_CS, Pin.OUT, value=1),
             dc=Pin(TFT_DC, Pin.OUT, value=0),
             rst=Pin(TFT_RST, Pin.OUT, value=1),
             buf=_tft_buf)
fb = tft.fb
bg = framebuf.FrameBuffer(_bg_buf, 160, 128, framebuf.RGB565)
btn_nav = Pin(BTN_NAV, Pin.IN, Pin.PULL_UP)
btn_sel = Pin(BTN_SELECT, Pin.IN, Pin.PULL_UP)
BUZZER_IDLE = 1 if BUZZER_ACTIVE_LOW else 0
Pin(BUZZER_PIN, Pin.OUT, value=BUZZER_IDLE)
main()