import asyncio
import json
import os
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Galga Lite - 8-bit edition
# The game is simulated at 540x820 but drawn on a tiny 135x205 canvas that is
# scaled up 4x (nearest-neighbour), which gives the chunky retro look and keeps
# drawing cheap in the browser.
# ---------------------------------------------------------------------------

WIDTH = 540
HEIGHT = 820
FPS = 60
SCALE = 4
LW, LH = WIDTH // SCALE, HEIGHT // SCALE  # 135 x 205 logical pixels

# Physics (pixels / second)
PLAYER_SPEED = 450
ACCELERATION = 2800
FRICTION = 0.92  # tuned per frame at 60 FPS, applied frame-rate independently

OBSTACLE_WIDTH = 52
OBSTACLE_HEIGHT = 52

# Limited retro palette
BG = (8, 8, 26)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 80)
RED = (255, 70, 70)
GREEN = (60, 220, 130)
BLUE = (60, 150, 255)
GREY = (150, 155, 190)

PAL = {
    "W": (255, 255, 255),
    "C": (90, 235, 255),
    "B": (50, 120, 240),
    "D": (22, 52, 150),
    "R": (255, 70, 70),
    "Y": (255, 220, 80),
    "O": (255, 140, 40),
}

PHASES = [
    {"name": "PHASE 1", "start": 0, "spawn_interval": 0.95, "speed_min": 140, "speed_max": 200},
    {"name": "PHASE 2", "start": 20, "spawn_interval": 0.72, "speed_min": 190, "speed_max": 270},
    {"name": "PHASE 3", "start": 40, "spawn_interval": 0.55, "speed_min": 250, "speed_max": 350},
    {"name": "PHASE 4", "start": 65, "spawn_interval": 0.40, "speed_min": 320, "speed_max": 420},
]

# ---------------------------------------------------------------------------
# High score: browser localStorage on the web, a file on desktop
# ---------------------------------------------------------------------------
IS_WEB = sys.platform == "emscripten"
HS_KEY = "galga_lite_highscore"


def load_high_score():
    try:
        if IS_WEB:
            from platform import window
            return int(window.localStorage.getItem(HS_KEY) or 0)
        if os.path.exists("highscore.json"):
            with open("highscore.json", "r") as f:
                return int(json.load(f).get("highscore", 0))
    except Exception:
        pass
    return 0


def save_high_score(score):
    try:
        if IS_WEB:
            from platform import window
            window.localStorage.setItem(HS_KEY, str(score))
        else:
            with open("highscore.json", "w") as f:
                json.dump({"highscore": score}, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 5x7 pixel font
# ---------------------------------------------------------------------------
_F = {
    "A": "01110 10001 10001 11111 10001 10001 10001",
    "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110",
    "D": "11100 10010 10001 10001 10001 10010 11100",
    "E": "11111 10000 10000 11110 10000 10000 11111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110",
    "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001",
    "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001",
    "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110",
    "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010",
    "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100",
    "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110",
    "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111",
    "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010",
    "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110",
    "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110",
    "9": "01110 10001 10001 01111 00001 00010 01100",
    ":": "00000 00100 00100 00000 00100 00100 00000",
    "-": "00000 00000 00000 11111 00000 00000 00000",
    "!": "00100 00100 00100 00100 00100 00000 00100",
    ".": "00000 00000 00000 00000 00000 01100 01100",
    " ": "00000 00000 00000 00000 00000 00000 00000",
}
FONT = {ch: rows.split() for ch, rows in _F.items()}
_text_cache = {}


def text_surface(text, color, scale=1):
    """Pre-rendered (and cached) pixel text with a 1px drop shadow."""
    key = (text, color, scale)
    surf = _text_cache.get(key)
    if surf is not None:
        return surf
    off = max(1, scale // 2)
    w = (len(text) * 6 - 1) * scale + off
    h = 7 * scale + off
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, ch in enumerate(text):
        rows = FONT.get(ch.upper(), FONT[" "])
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    x = (i * 6 + rx) * scale
                    y = ry * scale
                    surf.fill((0, 0, 0), (x + off, y + off, scale, scale))
    for i, ch in enumerate(text):
        rows = FONT.get(ch.upper(), FONT[" "])
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    surf.fill(color, ((i * 6 + rx) * scale, ry * scale, scale, scale))
    if len(_text_cache) > 300:
        _text_cache.clear()
    _text_cache[key] = surf
    return surf


def draw_text_center(surface, text, color, cx, y, scale=1):
    s = text_surface(text, color, scale)
    surface.blit(s, (cx - s.get_width() // 2, y))


# ---------------------------------------------------------------------------
# Pixel-art sprites (built once at startup)
# ---------------------------------------------------------------------------
SHIP_ART = [
    ".......W.......",
    "......WCW......",
    "......WCW......",
    ".....WWCWW.....",
    ".....WBCBW.....",
    "....WBBBBBW....",
    "..W.WBBDBBW.W..",
    "..BWBBBDBBBWB..",
    ".BBBBBBDBBBBBB.",
    ".BBDBBBDBBBDBB.",
    "BBDDBBBDBBBDDBB",
    "BRDD.BBDBB.DDRB",
    "B.D..BDDDB..D.B",
    ".....DD.DD.....",
    ".....O...O.....",
]


def make_ship_sprite():
    h, w = len(SHIP_ART), len(SHIP_ART[0])
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(SHIP_ART):
        assert len(row) == w, "ship row width"
        for x, ch in enumerate(row):
            if ch in PAL:
                surf.set_at((x, y), PAL[ch])
    return surf


def make_meteor_sprite(seed, size=13):
    rng = random.Random(seed)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = (size - 1) / 2.0
    radii = [rng.uniform(4.6, 6.3) for _ in range(16)]
    inside = set()
    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            ang = int(((__import__("math").atan2(dy, dx) + 3.14159) / 6.28319) * 16) % 16
            if (dx * dx + dy * dy) ** 0.5 <= radii[ang]:
                inside.add((x, y))
    for (x, y) in inside:
        edge = any((x + ax, y + ay) not in inside for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            col = (60, 44, 40)
        else:
            light = ((x - c) + (y - c)) / (2.0 * c)
            if light < -0.25:
                col = (178, 150, 120)
            elif light < 0.25:
                col = (134, 108, 90)
            else:
                col = (96, 76, 66)
        surf.set_at((x, y), col)
    for _ in range(3):  # craters
        cx, cy = rng.randint(3, size - 5), rng.randint(3, size - 5)
        for px, py in ((cx, cy), (cx + 1, cy), (cx, cy + 1)):
            if (px, py) in inside:
                surf.set_at((px, py), (70, 52, 46))
    for _ in range(2):  # hot embers
        px, py = rng.randint(3, size - 4), rng.randint(3, size - 4)
        if (px, py) in inside:
            surf.set_at((px, py), (255, 140, 40))
    return surf


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        k = max(0.0, self.life / self.max_life)
        c = (int(self.color[0] * k + BG[0] * (1 - k)),
             int(self.color[1] * k + BG[1] * (1 - k)),
             int(self.color[2] * k + BG[2] * (1 - k)))
        s = 2 if self.size >= 7 else 1
        surface.fill(c, (int(self.x) // SCALE, int(self.y) // SCALE, s, s))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, vx, vy, life, color, size):
        self.particles.append(Particle(x, y, vx, vy, life, color, size))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)


class Star:
    COLORS = [(110, 110, 160), (200, 200, 255), (255, 255, 255), (255, 230, 130)]

    def __init__(self):
        self.reset(True)

    def reset(self, random_y=False):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT) if random_y else -10
        self.speed = random.uniform(50, 200)
        self.big = self.speed > 150
        self.color = random.choice(Star.COLORS)

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > HEIGHT:
            self.reset()

    def draw(self, surface):
        s = 2 if self.big else 1
        surface.fill(self.color, (int(self.x) // SCALE, int(self.y) // SCALE, s, s))


class Obstacle:
    def __init__(self, x, speed, image):
        self.rect = pygame.Rect(x, -OBSTACLE_HEIGHT, OBSTACLE_WIDTH, OBSTACLE_HEIGHT)
        self.y = float(-OBSTACLE_HEIGHT)
        self.speed = speed
        self.passed = False
        self.image = image

    def update(self, dt):
        self.y += self.speed * dt
        self.rect.y = int(self.y)

    def draw(self, surface):
        surface.blit(self.image, (self.rect.x // SCALE, self.rect.y // SCALE))


class Button:
    def __init__(self, text, x, y, w, h, color, shade):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.shade = shade
        self.is_hovered = False

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        x, y = self.rect.x // SCALE, self.rect.y // SCALE
        w, h = self.rect.w // SCALE, self.rect.h // SCALE
        face = tuple(min(255, c + 40) for c in self.color) if self.is_hovered else self.color
        surface.fill(WHITE, (x, y, w, h))
        surface.fill(face, (x + 1, y + 1, w - 2, h - 2))
        surface.fill(self.shade, (x + 1, y + h - 3, w - 2, 2))
        draw_text_center(surface, self.text, WHITE, x + w // 2, y + (h - 14) // 2 - 1, 2)


def get_phase(elapsed_seconds):
    current = PHASES[0]
    for phase in PHASES:
        if elapsed_seconds >= phase["start"]:
            current = phase
        else:
            break
    return current


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def game_loop():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Galga Lite")

    low = pygame.Surface((LW, LH))          # the tiny retro canvas
    scaled = pygame.Surface((WIDTH, HEIGHT))  # only used while the screen shakes
    dim = pygame.Surface((LW, LH), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 165))

    ship_img = make_ship_sprite()
    meteor_imgs = [make_meteor_sprite(i) for i in range(4)]

    clock = pygame.time.Clock()
    stars = [Star() for _ in range(60)]
    ps = ParticleSystem()

    play_btn = Button("PLAY", WIDTH // 2 - 140, 460, 280, 64, (40, 110, 230), (22, 60, 150))
    retry_btn = Button("RETRY", WIDTH // 2 - 140, 580, 280, 64, (40, 170, 110), (22, 100, 70))

    player_rect = pygame.Rect(WIDTH // 2 - 32, HEIGHT - 100, 64, 64)
    player_x = float(player_rect.x)
    player_vx = 0.0
    shake_amount = 0.0

    obstacles = []
    game_state = "menu"
    score = 0
    high_score = load_high_score()
    saved_high = high_score
    elapsed = 0.0
    spawn_timer = 0.0
    phase_name = PHASES[0]["name"]

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        if dt > 0.1:
            dt = 0.1
        mouse_pos = pygame.mouse.get_pos()

        start_requested = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Use the event's own position so a touch tap registers immediately.
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "menu" and play_btn.rect.collidepoint(event.pos):
                    start_requested = True
                elif game_state == "gameover" and retry_btn.rect.collidepoint(event.pos):
                    start_requested = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if high_score > saved_high:
                        save_high_score(high_score)
                        saved_high = high_score
                    game_state = "menu"
                    obstacles.clear()
                elif game_state == "menu" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    start_requested = True
                elif game_state == "gameover" and event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                    start_requested = True

        if start_requested and game_state in ("menu", "gameover"):
            game_state = "playing"
            score, elapsed, spawn_timer = 0, 0.0, 0.0
            obstacles.clear()
            player_vx = 0.0
            player_x = float(player_rect.x)

        # ---- gameplay ----
        if game_state == "playing":
            elapsed += dt
            phase = get_phase(elapsed)
            phase_name = phase["name"]

            keys = pygame.key.get_pressed()
            move_input = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                move_input -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                move_input += 1
            # Touch / mouse hold: left half steers left, right half steers right
            if move_input == 0 and pygame.mouse.get_pressed()[0]:
                move_input = -1 if mouse_pos[0] < WIDTH / 2 else 1

            player_vx += move_input * ACCELERATION * dt
            if move_input == 0:
                player_vx *= FRICTION ** (dt * 60)
            player_vx = max(-PLAYER_SPEED, min(PLAYER_SPEED, player_vx))

            player_x += player_vx * dt
            if player_x < 10:
                player_x = 10
                player_vx = 0
            if player_x + player_rect.width > WIDTH - 10:
                player_x = WIDTH - 10 - player_rect.width
                player_vx = 0
            player_rect.x = int(player_x)

            if random.random() < 30 * dt:  # engine exhaust
                ps.emit(player_rect.centerx + random.randint(-8, 8), player_rect.bottom - 6,
                        random.uniform(-20, 20), random.uniform(100, 200),
                        0.35, (255, 170, 60), 3)

            spawn_timer += dt
            if spawn_timer >= phase["spawn_interval"]:
                spawn_timer = 0.0
                ox = random.randint(20, WIDTH - OBSTACLE_WIDTH - 20)
                ospeed = random.randint(phase["speed_min"], phase["speed_max"])
                obstacles.append(Obstacle(ox, ospeed, random.choice(meteor_imgs)))

            for obs in obstacles:
                obs.update(dt)
                if not obs.passed and obs.rect.top > player_rect.bottom:
                    obs.passed = True
                    score += 1
                    if score > high_score:
                        high_score = score

            obstacles = [o for o in obstacles if o.rect.top <= HEIGHT + 50]

            player_hit = player_rect.inflate(-24, -16)
            if any(player_hit.colliderect(o.rect.inflate(-12, -12)) for o in obstacles):
                game_state = "gameover"
                shake_amount = 24.0
                if high_score > saved_high:
                    save_high_score(high_score)
                    saved_high = high_score
                for _ in range(36):
                    ps.emit(player_rect.centerx, player_rect.centery,
                            random.uniform(-380, 380), random.uniform(-380, 380),
                            0.9, random.choice(((255, 150, 50), (255, 220, 80), (255, 90, 60))),
                            random.randint(4, 9))

        # ---- update effects ----
        ps.update(dt)
        for star in stars:
            star.update(dt)

        # ---- draw (all on the tiny canvas) ----
        low.fill(BG)
        for star in stars:
            star.draw(low)
        ps.draw(low)

        cx = LW // 2
        if game_state == "menu":
            play_btn.update(mouse_pos)
            draw_text_center(low, "GALGA", YELLOW, cx, 26, 4)
            draw_text_center(low, "LITE", (255, 140, 40), cx, 58, 4)
            draw_text_center(low, "BEST: " + str(high_score), GREY, cx, 96)
            play_btn.draw(low)
            draw_text_center(low, "MOVE: ARROWS OR TOUCH", GREY, cx, 150)
            draw_text_center(low, "DODGE THE ROCKS!", GREY, cx, 162)
        else:
            for obs in obstacles:
                obs.draw(low)
            if game_state == "playing":
                low.blit(ship_img, (player_rect.centerx // SCALE - 7, player_rect.centery // SCALE - 7))
            draw_text_center(low, "SCORE: " + str(score), WHITE, cx, 6, 2)
            draw_text_center(low, phase_name, YELLOW, cx, 24)
            if game_state == "gameover":
                retry_btn.update(mouse_pos)
                low.blit(dim, (0, 0))
                draw_text_center(low, "GAME", RED, cx, 36, 4)
                draw_text_center(low, "OVER", RED, cx, 68, 4)
                draw_text_center(low, "SCORE: " + str(score), WHITE, cx, 104, 2)
                draw_text_center(low, "BEST: " + str(high_score), YELLOW, cx, 124)
                retry_btn.draw(low)
                draw_text_center(low, "PRESS R OR TAP", GREY, cx, 168)

        # ---- present: nearest-neighbour upscale (shake by shifting the result) ----
        if shake_amount > 0:
            amt = int(shake_amount) // SCALE
            ox = random.randint(-amt, amt) * SCALE
            oy = random.randint(-amt, amt) * SCALE
            pygame.transform.scale(low, (WIDTH, HEIGHT), scaled)
            screen.fill(BG)
            screen.blit(scaled, (ox, oy))
            shake_amount = max(0.0, shake_amount - 60 * dt)
        else:
            pygame.transform.scale(low, (WIDTH, HEIGHT), screen)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    try:
        loop = asyncio.get_running_l