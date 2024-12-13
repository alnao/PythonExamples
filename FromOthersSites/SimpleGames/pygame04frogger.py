"""
pip install pygame
preso spunto dalla https://www.youtube.com/watch?v=k1GcyPwf4WI
build for me a game in python (and pygame if you need) that is similar to the video game frogger. there should be visual and i can control with my arrows to move
modifica il gioco aggiungendo un menu iniziale, migliora la grafica mettendo il personaggio come una icona di un uomo, aumentando il livello deve aumentare la velocità degli ostacoli , aggiungi che il player ha 3 vite, finite le vite deve compare la scritta "sei morto" e ritorna al menu principale
il personaggio deve essere di colori umani, le barre laterali di colori diversi e dovrebbero sembrare delle automobili, aggiungi la possiblità di mettere in pausa con la lettera p
Migliorare ulteriormente l'aspetto delle auto, Aggiungere animazioni per il personaggio, Modificare i colori o lo stile del menu di pausa, Aggiungere effetti particellari per le collisioni

"""

import pygame
import random
import math
from typing import List

pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PLAYER_SIZE = 40
OBSTACLE_HEIGHT = 40
OBSTACLE_WIDTH = 80
LANE_HEIGHT = 60
MOVE_DISTANCE = 40
FPS = 60

# Colors
WHITE = (255, 255, 255)
GREEN = (34, 139, 34)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
SKIN_COLOR = (255, 206, 180)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)
DARK_BLUE = (0, 0, 139)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 6)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 5)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.life = 1.0  # Full opacity
        self.decay = random.uniform(0.02, 0.05)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= self.decay
        self.size = max(0, self.size - 0.1)
        return self.life > 0

    def draw(self, screen):
        alpha = int(self.life * 255)
        particle_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, (*self.color, alpha), 
                         (self.size, self.size), self.size)
        screen.blit(particle_surface, (int(self.x - self.size), int(self.y - self.size)))

class Player:
    def __init__(self):
        self.rect = pygame.Rect(WINDOW_WIDTH // 2, WINDOW_HEIGHT - PLAYER_SIZE - 10,
                              PLAYER_SIZE, PLAYER_SIZE)
        self.lives = 3
        self.animation_frame = 0
        self.animation_timer = 0
        self.moving = False
        self.direction = "up"
        self.create_animation_frames()
        
    def create_animation_frames(self):
        # Create different animation frames for each direction
        self.frames = {
            "up": [], "down": [], "left": [], "right": []
        }
        
        for direction in self.frames.keys():
            for frame in range(4):  # 4 frames per direction
                surface = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
                
                # Head
                head_bob = math.sin(frame * math.pi/2) * 2  # Bob up and down
                pygame.draw.circle(surface, SKIN_COLOR, 
                                 (PLAYER_SIZE//2, PLAYER_SIZE//4 + head_bob), 
                                 PLAYER_SIZE//4)
                
                # Body (shifts based on direction and frame)
                if direction in ["left", "right"]:
                    body_shift = math.sin(frame * math.pi/2) * 3
                    body_start = (PLAYER_SIZE//2 + (body_shift if direction == "right" else -body_shift), 
                                PLAYER_SIZE//2)
                else:
                    body_shift = math.sin(frame * math.pi/2) * 2
                    body_start = (PLAYER_SIZE//2, PLAYER_SIZE//2 + body_shift)
                
                pygame.draw.line(surface, BLUE, body_start,
                               (PLAYER_SIZE//2, PLAYER_SIZE*3//4), 4)
                
                # Arms (swing based on movement)
                arm_swing = math.sin(frame * math.pi/2) * 10
                if direction in ["left", "right"]:
                    pygame.draw.line(surface, SKIN_COLOR,
                                   (PLAYER_SIZE//2, PLAYER_SIZE*2//3),
                                   (PLAYER_SIZE//4 - arm_swing, PLAYER_SIZE*2//3), 3)
                    pygame.draw.line(surface, SKIN_COLOR,
                                   (PLAYER_SIZE//2, PLAYER_SIZE*2//3),
                                   (PLAYER_SIZE*3//4 + arm_swing, PLAYER_SIZE*2//3), 3)
                else:
                    pygame.draw.line(surface, SKIN_COLOR,
                                   (PLAYER_SIZE//4, PLAYER_SIZE*2//3 - arm_swing),
                                   (PLAYER_SIZE*3//4, PLAYER_SIZE*2//3 + arm_swing), 3)
                
                # Legs (alternate based on movement)
                leg_swing = math.sin(frame * math.pi/2) * 15
                if direction in ["left", "right"]:
                    pygame.draw.line(surface, BROWN,
                                   (PLAYER_SIZE//2, PLAYER_SIZE*3//4),
                                   (PLAYER_SIZE//4 - leg_swing, PLAYER_SIZE), 3)
                    pygame.draw.line(surface, BROWN,
                                   (PLAYER_SIZE//2, PLAYER_SIZE*3//4),
                                   (PLAYER_SIZE*3//4 + leg_swing, PLAYER_SIZE), 3)
                else:
                    pygame.draw.line(surface, BROWN,
                                   (PLAYER_SIZE//2, PLAYER_SIZE*3//4),
                                   (PLAYER_SIZE//4 - leg_swing, PLAYER_SIZE), 3)
                    pygame.draw.line(surface, BROWN,
                                   (PLAYER_SIZE//2, PLAYER_SIZE*3//4),
                                   (PLAYER_SIZE*3//4 + leg_swing, PLAYER_SIZE), 3)
                
                self.frames[direction].append(surface)
    
    def move(self, dx, dy):
        new_x = max(0, min(WINDOW_WIDTH - PLAYER_SIZE, self.rect.x + dx))
        new_y = max(0, min(WINDOW_HEIGHT - PLAYER_SIZE, self.rect.y + dy))
        if dx > 0: self.direction = "right"
        elif dx < 0: self.direction = "left"
        elif dy > 0: self.direction = "down"
        elif dy < 0: self.direction = "up"
        self.rect.x = new_x
        self.rect.y = new_y
        self.moving = True
        
    def update(self):
        if self.moving:
            self.animation_timer += 1
            if self.animation_timer >= 5:  # Speed of animation
                self.animation_timer = 0
                self.animation_frame = (self.animation_frame + 1) % 4
        self.moving = False
    
    def draw(self, screen):
        screen.blit(self.frames[self.direction][self.animation_frame], self.rect)

class Car:
    def __init__(self, y, speed, direction=1, level=1):
        self.speed = speed * direction * (1 + (level - 1) * 0.2)
        if direction > 0:
            x = -OBSTACLE_WIDTH
        else:
            x = WINDOW_WIDTH
        self.rect = pygame.Rect(x, y, OBSTACLE_WIDTH, OBSTACLE_HEIGHT)
        self.direction = direction
        self.color = random.choice([RED, YELLOW, DARK_BLUE, GREEN, ORANGE, PURPLE])
        self.car_type = random.choice(["sedan", "sport", "truck"])
        self.wheel_rotation = 0
        
    def draw(self, screen):
        # Main car body
        if self.car_type == "sedan":
            # Rounded rectangle for car body
            pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
            # Roof
            roof_height = self.rect.height // 2
            roof_rect = pygame.Rect(self.rect.x + self.rect.width//4,
                                  self.rect.y - roof_height//2,
                                  self.rect.width//2,
                                  roof_height)
            pygame.draw.rect(screen, self.color, roof_rect, border_radius=5)
            
        elif self.car_type == "sport":
            # Sleek sports car design
            points = [
                (self.rect.x, self.rect.bottom),
                (self.rect.x + self.rect.width * 0.2, self.rect.y),
                (self.rect.x + self.rect.width * 0.8, self.rect.y),
                (self.rect.right, self.rect.bottom)
            ]
            pygame.draw.polygon(screen, self.color, points)
            
        else:  # truck
            # Cab
            cab_width = self.rect.width // 3
            pygame.draw.rect(screen, self.color, 
                           (self.rect.x, self.rect.y, cab_width, self.rect.height))
            # Cargo area
            pygame.draw.rect(screen, self.color, 
                           (self.rect.x + cab_width, self.rect.y + 5,
                            self.rect.width - cab_width, self.rect.height - 5))
        
        # Windows
        if self.car_type != "truck":
            window_width = self.rect.width // 4
            window_height = self.rect.height // 2
            window_y = self.rect.y + (self.rect.height - window_height) // 4
            
            pygame.draw.rect(screen, BLACK, 
                           (self.rect.x + 5, window_y, window_width, window_height))
            pygame.draw.rect(screen, BLACK, 
                           (self.rect.right - window_width - 5, window_y,
                            window_width, window_height))
        else:
            # Truck cabin window
            window_width = self.rect.width // 4
            window_height = self.rect.height // 2
            window_y = self.rect.y + (self.rect.height - window_height) // 4
            pygame.draw.rect(screen, BLACK, 
                           (self.rect.x + 5, window_y, window_width, window_height))
        
        # Wheels with rotation
        self.wheel_rotation = (self.wheel_rotation + self.speed) % 360
        wheel_radius = 6
        for wheel_x in [self.rect.x + wheel_radius + 5, self.rect.right - wheel_radius - 5]:
            wheel_y = self.rect.bottom - wheel_radius - 2
            pygame.draw.circle(screen, BLACK, (wheel_x, wheel_y), wheel_radius)
            # Wheel spokes for animation
            end_x = wheel_x + math.cos(math.radians(self.wheel_rotation)) * wheel_radius
            end_y = wheel_y + math.sin(math.radians(self.wheel_rotation)) * wheel_radius
            pygame.draw.line(screen, GRAY, (wheel_x, wheel_y), (end_x, end_y), 2)
        
        # Headlights/Taillights
        light_radius = 3
        if self.direction > 0:
            pygame.draw.circle(screen, YELLOW, 
                             (self.rect.right - 3, self.rect.centery - 5), light_radius)
            pygame.draw.circle(screen, RED, 
                             (self.rect.x + 3, self.rect.centery - 5), light_radius)
        else:
            pygame.draw.circle(screen, YELLOW, 
                             (self.rect.x + 3, self.rect.centery - 5), light_radius)
            pygame.draw.circle(screen, RED, 
                             (self.rect.right - 3, self.rect.centery - 5), light_radius)
    
    def move(self):
        self.rect.x += self.speed
        if self.speed > 0 and self.rect.left > WINDOW_WIDTH:
            self.rect.right = 0
        elif self.speed < 0 and self.rect.right < 0:
            self.rect.left = WINDOW_WIDTH

class Button:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.font = pygame.font.Font(None, 36)
        self.hover = False
        
    def draw(self, screen):
        color = tuple(min(c + 30, 255) for c in self.color) if self.hover else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=10)  # Border
        
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)
        
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Frogger Clone")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "menu"
        self.player = Player()
        self.cars = []
        self.particles: List[Particle] = []
        self.score = 0
        self.level = 1
        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        
        # Create buttons
        button_width = 200
        button_height = 50
        center_x = WINDOW_WIDTH // 2 - button_width // 2
        self.start_button = Button(center_x, 250, button_width, button_height, "Start Game", GREEN)
        self.quit_button = Button(center_x, 350, button_width, button_height, "Quit", RED)
        self.resume_button = Button(center_x, 250, button_width, button_height, "Resume", GREEN)
        
        # Create background gradient
        self.background = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            color_value = int(255 * (1 - y/WINDOW_HEIGHT))
            color = (0, 0, color_value//2)  # Dark blue gradient
            pygame.draw.line(self.background, color, (0, y), (WINDOW_WIDTH, y))
    def setup_obstacles(self):
        self.cars.clear()
        # Create 5 lanes of cars
        for i in range(5):
            y = 100 + i * LANE_HEIGHT
            direction = 1 if i % 2 == 0 else -1
            speed = random.uniform(2, 5)
            # Add 3 cars per lane
            for _ in range(3):
                self.cars.append(Car(y, speed, direction, self.level))
    
    def create_collision_particles(self, x, y, color):
        for _ in range(20):  # Number of particles
            self.particles.append(Particle(x, y, color))
                
    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        self.start_button.update(mouse_pos)
        self.quit_button.update(mouse_pos)
        if self.state == "paused":
            self.resume_button.update(mouse_pos)
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state in ["menu", "game_over"]:
                    if self.start_button.is_clicked(event.pos):
                        self.start_new_game()
                    elif self.quit_button.is_clicked(event.pos):
                        self.running = False
                elif self.state == "paused":
                    if self.resume_button.is_clicked(event.pos):
                        self.state = "playing"
                    elif self.quit_button.is_clicked(event.pos):
                        self.state = "menu"
                        
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and self.state in ["playing", "paused"]:
                    self.state = "playing" if self.state == "paused" else "paused"
                elif self.state == "playing":
                    if event.key == pygame.K_UP:
                        self.player.move(0, -MOVE_DISTANCE)
                    elif event.key == pygame.K_DOWN:
                        self.player.move(0, MOVE_DISTANCE)
                    elif event.key == pygame.K_LEFT:
                        self.player.move(-MOVE_DISTANCE, 0)
                    elif event.key == pygame.K_RIGHT:
                        self.player.move(MOVE_DISTANCE, 0)
    
    def start_new_game(self):
        self.state = "playing"
        self.score = 0
        self.level = 1
        self.player = Player()
        self.setup_obstacles()
        self.particles.clear()
    
    def check_collisions(self):
        for car in self.cars:
            if self.player.rect.colliderect(car.rect):
                self.create_collision_particles(self.player.rect.centerx, 
                                             self.player.rect.centery, 
                                             car.color)
                self.player.lives -= 1
                if self.player.lives <= 0:
                    self.state = "game_over"
                self.reset_player()
                return
        
        # Check if player reached the top
        if self.player.rect.y < 50:
            self.score += 1
            if self.score % 3 == 0:  # Level up every 3 points
                self.level += 1
                self.setup_obstacles()
            self.reset_player()
    
    def reset_player(self):
        self.player.rect.x = WINDOW_WIDTH // 2
        self.player.rect.y = WINDOW_HEIGHT - PLAYER_SIZE - 10
    
    def update(self):
        if self.state == "playing":
            self.player.update()
            for car in self.cars:
                car.move()
            self.check_collisions()
            
            # Update particles
            self.particles = [p for p in self.particles if p.update()]
    
    def draw_menu(self):
        # Draw animated background
        self.screen.blit(self.background, (0, 0))
        
        # Draw title with glow effect
        title_text = "FROGGER CLONE"
        glow_surfaces = []
        for i in range(3):
            size = 72 + i * 4
            font = pygame.font.Font(None, size)
            text_surface = font.render(title_text, True, (0, 0, 255 - i * 50))
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 150))
            glow_surfaces.append((text_surface, text_rect))
            
        for surface, rect in reversed(glow_surfaces):
            self.screen.blit(surface, rect)
        
        self.start_button.draw(self.screen)
        self.quit_button.draw(self.screen)
    
    def draw_game(self):
        self.screen.blit(self.background, (0, 0))
        
        # Draw side borders with gradient effect
        for i in range(50):
            color = (max(0, 100-i*2), max(0, 150-i*2), max(0, 200-i*2))
            pygame.draw.line(self.screen, color, (0, i), (WINDOW_WIDTH, i))
            pygame.draw.line(self.screen, color, (0, WINDOW_HEIGHT-i), 
                           (WINDOW_WIDTH, WINDOW_HEIGHT-i))
        
        # Draw lane markers
        for i in range(1, 6):
            y = i * LANE_HEIGHT + 50
            for x in range(0, WINDOW_WIDTH, 40):
                pygame.draw.rect(self.screen, WHITE, 
                               (x, y, 20, 3))
        
        # Draw score and level with shadow effect
        texts = [
            (f'Score: {self.score}', (10, 10)),
            (f'Level: {self.level}', (200, 10)),
            (f'Lives: {self.player.lives}', (400, 10))
        ]
        
        for text, pos in texts:
            # Draw shadow
            shadow_surface = self.font.render(text, True, BLACK)
            self.screen.blit(shadow_surface, (pos[0] + 2, pos[1] + 2))
            # Draw text
            text_surface = self.font.render(text, True, WHITE)
            self.screen.blit(text_surface, pos)
        
        # Draw cars and particles
        for car in self.cars:
            car.draw(self.screen)
        for particle in self.particles:
            particle.draw(self.screen)
        self.player.draw(self.screen)
    
    def draw_pause(self):
        # Draw semi-transparent overlay with ripple effect
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0,0))
        
        # Draw pause menu with glow effect
        pause_text = "PAUSED"
        for i in range(3):
            size = 72 + i * 4
            font = pygame.font.Font(None, size)
            text_surface = font.render(pause_text, True, (0, 0, 255 - i * 50))
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 150))
            self.screen.blit(text_surface, text_rect)
        
        self.resume_button.draw(self.screen)
        self.quit_button.draw(self.screen)
    
    def draw_game_over(self):
        self.screen.fill(BLACK)
        
        # Draw game over text with pulsing effect
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 50
        game_over_text = self.big_font.render("SEI MORTO!", True, 
                                            (255 - pulse, 0, 0))
        score_text = self.font.render(f'Punteggio Finale: {self.score}', 
                                    True, WHITE)
        
        game_over_rect = game_over_text.get_rect(center=(WINDOW_WIDTH//2, 150))
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH//2, 200))
        
        self.screen.blit(game_over_text, game_over_rect)
        self.screen.blit(score_text, score_rect)
        
        self.start_button.draw(self.screen)
        self.quit_button.draw(self.screen)
    
    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        elif self.state == "paused":
            self.draw_game()
            self.draw_pause()
        elif self.state == "game_over":
            self.draw_game_over()
            
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        
        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()


