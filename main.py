import asyncio
import random
import sys
import math
import pygame

# Constants
WIDTH = 540
HEIGHT = 820
FPS = 60

# Physics
PLAYER_SPEED = 450
ACCELERATION = 2800
FRICTION = 0.92
MAX_TILT = 15

# Visuals
OBSTACLE_WIDTH = 52
OBSTACLE_HEIGHT = 52
BG_TOP = (8, 15, 35)
BG_BOTTOM = (2, 6, 18)
WHITE = (240, 245, 255)
SHIP_COLOR = (90, 230, 255)
OBSTACLE_COLOR = (255, 116, 116)
ACCENT = (255, 198, 111)

PHASES = [
    {"name": "Phase 1", "start": 0, "spawn_interval": 0.95, "speed_min": 140, "speed_max": 200},
    {"name": "Phase 2", "start": 20, "spawn_interval": 0.72, "speed_min": 190, "speed_max": 270},
    {"name": "Phase 3", "start": 40, "spawn_interval": 0.55, "speed_min": 250, "speed_max": 350},
    {"name": "Phase 4", "start": 65, "spawn_interval": 0.40, "speed_min": 320, "speed_max": 420},
]

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
        alpha = int((self.life / self.max_life) * 255)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))

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
    def __init__(self):
        self.reset(True)

    def reset(self, random_y=False):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT) if random_y else -10
        self.speed = random.uniform(50, 200)
        self.size = random.uniform(1, 3)
        self.color = random.choice([(200, 200, 255), (255, 255, 255), (255, 255, 200)])

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > HEIGHT:
            self.reset()

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.size))

class Obstacle:
    def __init__(self, x, speed, image=None):
        self.rect = pygame.Rect(x, -OBSTACLE_HEIGHT, OBSTACLE_WIDTH, OBSTACLE_HEIGHT)
        self.speed = speed
        self.passed = False
        self.image = image
        self.angle = 0
        self.rotation_speed = random.uniform(-100, 100)

    def update(self, dt):
        self.rect.y += int(self.speed * dt)
        self.angle += self.rotation_speed * dt

    def draw(self, surface):
        if self.image:
            rotated = pygame.transform.rotate(self.image, self.angle)
            rect = rotated.get_rect(center=self.rect.center)
            surface.blit(rotated, rect)
        else:
            pygame.draw.rect(surface, OBSTACLE_COLOR, self.rect, border_radius=10)

def get_phase(elapsed_seconds):
    current = PHASES[0]
    for phase in PHASES:
        if elapsed_seconds >= phase["start"]:
            current = phase
        else:
            break
    return current

def create_gradient_surface():
    surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        color = (
            int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio),
            int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio),
            int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio),
        )
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))
    return surface

def draw_text_center(surface, text, font, color, center_x, y, shadow=True):
    if shadow:
        s_img = font.render(text, True, (0, 0, 0))
        s_rect = s_img.get_rect(midtop=(center_x + 2, y + 2))
        surface.blit(s_img, s_rect)
    img = font.render(text, True, color)
    rect = img.get_rect(midtop=(center_x, y))
    surface.blit(img, rect)

async def game_loop():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Galga Lite - Enhanced")

    # Fonts
    try:
        title_font = pygame.font.Font(None, 72)
        ui_font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)
    except:
        title_font = pygame.font.SysFont("consolas", 64, bold=True)
        ui_font = pygame.font.SysFont("consolas", 28)
        small_font = pygame.font.SysFont("consolas", 20)

    # Assets
    try:
        ship_img = pygame.image.load("assets/ship.png").convert_alpha()
        ship_img = pygame.transform.scale(ship_img, (64, 64))
        meteor_img = pygame.image.load("assets/meteor.png").convert_alpha()
        meteor_img = pygame.transform.scale(meteor_img, (OBSTACLE_WIDTH, OBSTACLE_HEIGHT))
    except:
        ship_img = None
        meteor_img = None

    clock = pygame.time.Clock()
    bg_surface = create_gradient_surface()
    stars = [Star() for _ in range(60)]
    ps = ParticleSystem()

    # Game State
    player_rect = pygame.Rect(WIDTH // 2 - 32, HEIGHT - 100, 64, 64)
    player_vx = 0.0
    tilt = 0.0
    shake_amount = 0
    
    obstacles = []
    game_state = "menu"
    score = 0
    elapsed = 0.0
    spawn_timer = 0.0
    phase_name = PHASES[0]["name"]

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        if dt > 0.1: dt = 0.1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game_state == "menu" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    game_state = "playing"
                    score, elapsed, spawn_timer = 0, 0.0, 0.0
                    obstacles.clear()
                    player_vx = 0
                elif game_state == "gameover" and event.key in (pygame.K_r, pygame.K_RETURN):
                    game_state = "playing"
                    score, elapsed, spawn_timer = 0, 0.0, 0.0
                    obstacles.clear()
                    player_vx = 0
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # Gameplay Logic
        if game_state == "playing":
            elapsed += dt
            phase = get_phase(elapsed)
            phase_name = phase["name"]

            keys = pygame.key.get_pressed()
            move_input = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: move_input -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: move_input += 1

            # Smooth Physics
            if move_input != 0:
                player_vx += move_input * ACCELERATION * dt
                tilt += (-move_input * MAX_TILT - tilt) * 0.1
            else:
                player_vx *= FRICTION
                tilt *= FRICTION

            player_vx = max(-PLAYER_SPEED, min(PLAYER_SPEED, player_vx))
            player_rect.x += int(player_vx * dt)
            
            # Bounds
            if player_rect.left < 10:
                player_rect.left = 10
                player_vx = 0
            if player_rect.right > WIDTH - 10:
                player_rect.right = WIDTH - 10
                player_vx = 0

            # Thruster Particles
            if random.random() < 0.5:
                ps.emit(player_rect.centerx + random.randint(-10, 10), player_rect.bottom - 10, 
                        random.uniform(-20, 20), random.uniform(100, 200), 
                        0.4, (100, 200, 255), random.randint(2, 4))

            # Spawning
            spawn_timer += dt
            if spawn_timer >= phase["spawn_interval"]:
                spawn_timer = 0.0
                ox = random.randint(20, WIDTH - OBSTACLE_WIDTH - 20)
                ospeed = random.randint(phase["speed_min"], phase["speed_max"])
                obstacles.append(Obstacle(ox, ospeed, meteor_img))

            for obs in obstacles:
                obs.update(dt)
                if not obs.passed and obs.rect.top > player_rect.bottom:
                    obs.passed = True
                    score += 1

            obstacles = [obs for obs in obstacles if obs.rect.top <= HEIGHT + 50]

            # Collision
            if any(player_rect.colliderect(obs.rect) for obs in obstacles):
                game_state = "gameover"
                shake_amount = 20
                for _ in range(30):
                    ps.emit(player_rect.centerx, player_rect.centery, 
                            random.uniform(-300, 300), random.uniform(-300, 300), 
                            0.8, (255, 150, 50), random.randint(4, 8))

        # Rendering
        ps.update(dt)
        for star in stars: star.update(dt)

        render_offset = (0, 0)
        if shake_amount > 0:
            render_offset = (random.randint(-shake_amount, shake_amount), random.randint(-shake_amount, shake_amount))
            shake_amount -= 1

        screen.blit(bg_surface, (0, 0))
        for star in stars: star.draw(screen)
        ps.draw(screen)

        if game_state == "menu":
            draw_text_center(screen, "GALGA LITE", title_font, WHITE, WIDTH // 2, 250)
            draw_text_center(screen, "NEO EDITION", small_font, ACCENT, WIDTH // 2, 310)
            draw_text_center(screen, "Press SPACE to Begin", ui_font, WHITE, WIDTH // 2, 450)
        else:
            if game_state == "playing":
                if ship_img:
                    rotated_ship = pygame.transform.rotate(ship_img, tilt)
                    ship_draw_rect = rotated_ship.get_rect(center=player_rect.center)
                    screen.blit(rotated_ship, (ship_draw_rect.x + render_offset[0], ship_draw_rect.y + render_offset[1]))
                else:
                    pygame.draw.polygon(screen, SHIP_COLOR, [(player_rect.centerx, player_rect.top), (player_rect.left, player_rect.bottom), (player_rect.right, player_rect.bottom)])

            for obs in obstacles:
                obs.draw(screen)

            draw_text_center(screen, f"SCORE: {score}", ui_font, WHITE, WIDTH // 2, 30)
            draw_text_center(screen, f"{phase_name}", small_font, ACCENT, WIDTH // 2, 70)

            if game_state == "gameover":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                screen.blit(overlay, (0, 0))
                draw_text_center(screen, "SYSTEM FAILURE", title_font, (255, 80, 80), WIDTH // 2, 300)
                draw_text_center(screen, f"FINAL SCORE: {score}", ui_font, WHITE, WIDTH // 2, 380)
                draw_text_center(screen, "Press R to Reboot", small_font, ACCENT, WIDTH // 2, 440)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(game_loop())
    except RuntimeError:
        asyncio.run(game_loop())



