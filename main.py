import asyncio
import random
import sys

import pygame

WIDTH = 540
HEIGHT = 820
FPS = 60

PLAYER_SPEED = 360
OBSTACLE_WIDTH = 52
OBSTACLE_HEIGHT = 52

BG_TOP = (8, 15, 35)
BG_BOTTOM = (2, 6, 18)
WHITE = (240, 245, 255)
SHIP_COLOR = (90, 230, 255)
OBSTACLE_COLOR = (255, 116, 116)
ACCENT = (255, 198, 111)

PHASES = [
    {
        "name": "Phase 1",
        "start": 0,
        "spawn_interval": 0.95,
        "speed_min": 130,
        "speed_max": 190,
    },
    {
        "name": "Phase 2",
        "start": 20,
        "spawn_interval": 0.72,
        "speed_min": 175,
        "speed_max": 250,
    },
    {
        "name": "Phase 3",
        "start": 40,
        "spawn_interval": 0.58,
        "speed_min": 230,
        "speed_max": 315,
    },
    {
        "name": "Phase 4",
        "start": 60,
        "spawn_interval": 0.44,
        "speed_min": 290,
        "speed_max": 380,
    },
]


class Obstacle:
    def __init__(self, x, speed):
        self.rect = pygame.Rect(x, -OBSTACLE_HEIGHT, OBSTACLE_WIDTH, OBSTACLE_HEIGHT)
        self.speed = speed
        self.passed = False

    def update(self, dt):
        self.rect.y += int(self.speed * dt)

    def draw(self, surface):
        pygame.draw.rect(surface, OBSTACLE_COLOR, self.rect, border_radius=10)
        core = self.rect.inflate(-20, -20)
        pygame.draw.rect(surface, (255, 160, 145), core, border_radius=8)


def get_phase(elapsed_seconds):
    current = PHASES[0]
    for phase in PHASES:
        if elapsed_seconds >= phase["start"]:
            current = phase
        else:
            break
    return current


def draw_gradient(surface):
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        color = (
            int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio),
            int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio),
            int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio),
        )
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))


def draw_player(surface, rect):
    nose = (rect.centerx, rect.y)
    left = (rect.x, rect.bottom)
    right = (rect.right, rect.bottom)
    pygame.draw.polygon(surface, SHIP_COLOR, [nose, left, right])
    cockpit = pygame.Rect(rect.centerx - 7, rect.y + 13, 14, 16)
    pygame.draw.rect(surface, WHITE, cockpit, border_radius=4)
    pygame.draw.rect(surface, ACCENT, (rect.centerx - 2, rect.bottom - 16, 4, 14), border_radius=2)


def draw_text(surface, text, font, color, x, y):
    img = font.render(text, True, color)
    surface.blit(img, (x, y))


def draw_text_center(surface, text, font, color, center_x, y):
    img = font.render(text, True, color)
    rect = img.get_rect(midtop=(center_x, y))
    surface.blit(img, rect)


async def game_loop():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Galga Lite")

    title_font = pygame.font.SysFont("consolas", 48, bold=True)
    ui_font = pygame.font.SysFont("consolas", 24)
    small_font = pygame.font.SysFont("consolas", 18)

    clock = pygame.time.Clock()

    player = pygame.Rect(WIDTH // 2 - 24, HEIGHT - 92, 48, 58)
    obstacles = []

    game_state = "menu"
    score = 0
    elapsed = 0.0
    spawn_timer = 0.0
    phase_name = PHASES[0]["name"]

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game_state == "menu" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    game_state = "playing"
                    score = 0
                    elapsed = 0.0
                    spawn_timer = 0.0
                    obstacles.clear()
                    player.x = WIDTH // 2 - player.width // 2
                elif game_state == "gameover" and event.key in (pygame.K_r, pygame.K_RETURN):
                    game_state = "playing"
                    score = 0
                    elapsed = 0.0
                    spawn_timer = 0.0
                    obstacles.clear()
                    player.x = WIDTH // 2 - player.width // 2
                elif event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()
        if game_state == "playing":
            elapsed += dt
            phase = get_phase(elapsed)
            phase_name = phase["name"]

            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.x -= int(PLAYER_SPEED * dt)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.x += int(PLAYER_SPEED * dt)
            player.x = max(16, min(WIDTH - player.width - 16, player.x))

            spawn_timer += dt
            if spawn_timer >= phase["spawn_interval"]:
                spawn_timer = 0.0
                lane_min = 18
                lane_max = WIDTH - OBSTACLE_WIDTH - 18
                ox = random.randint(lane_min, lane_max)
                ospeed = random.randint(phase["speed_min"], phase["speed_max"])
                obstacles.append(Obstacle(ox, ospeed))

            for obs in obstacles:
                obs.update(dt)
                if not obs.passed and obs.rect.top > player.bottom:
                    obs.passed = True
                    score += 1

            obstacles = [obs for obs in obstacles if obs.rect.top <= HEIGHT + 10]

            if any(player.colliderect(obs.rect) for obs in obstacles):
                game_state = "gameover"

        draw_gradient(screen)

        if game_state == "menu":
            cx = WIDTH // 2
            draw_text_center(screen, "GALGA LITE", title_font, WHITE, cx, 220)
            draw_text_center(screen, "Avoid incoming obstacles", ui_font, (180, 215, 255), cx, 320)
            draw_text_center(screen, "Move: Left/Right or A/D", small_font, (160, 190, 230), cx, 370)
            draw_text_center(screen, "Press SPACE to Start", ui_font, ACCENT, cx, 420)
            draw_text_center(screen, "Esc to Exit", small_font, (160, 190, 230), cx, 460)
        else:
            draw_player(screen, player)

            for obs in obstacles:
                obs.draw(screen)

            draw_text(screen, f"Score: {score}", ui_font, WHITE, 18, 16)
            draw_text(screen, "Scoring: obstacles passed", small_font, (170, 205, 240), 18, 42)
            draw_text(screen, f"Phase: {phase_name}", ui_font, WHITE, 18, 66)
            draw_text(screen, f"Time: {elapsed:0.1f}s", ui_font, WHITE, 18, 96)

            if game_state == "gameover":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 165))
                screen.blit(overlay, (0, 0))
                draw_text(screen, "GAME OVER", title_font, (255, 145, 145), 135, 290)
                draw_text(screen, f"Final Score: {score}", ui_font, WHITE, 185, 370)
                draw_text(screen, "Press R or Enter to Restart", small_font, ACCENT, 148, 420)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(game_loop())
    else:
        running_loop.create_task(game_loop())
