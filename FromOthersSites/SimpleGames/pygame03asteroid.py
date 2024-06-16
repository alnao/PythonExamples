# ASTEROID GAME  #see https://realpython.com/asteroids-game-python/

import pygame# pygame==2.0.0
import os
from pygame.math import Vector2
from pygame.transform import rotozoom
from pygame.math import Vector2
from pygame import Color
import random
#import io
#from urllib.request import urlopen

UP = Vector2(0, -1)
NUMBER_ASTEROD=6
NUMBER_BULLET=10

class SpaceRocks:
    def __init__(self): #metodo per inizializzare il gioco: crea schermo e oggetti (nave e asteriodi)
        self._init_pygame()
        self.utils=GameUtils()
        self.screen = pygame.display.set_mode((800, 600))
        self.background = self.utils.load_sprite("space.jpg", False)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 64)
        self.message = ""
        self.bullets = []
        self.asteroids = []
        self.spaceship = Spaceship((400, 300), self.append_bullet) #self.spaceship = GameObject((400, 300), load_sprite("spaceship.png",scale=True), (0, 0))
        self.asteroids = [ #self.asteroid = GameObject((400, 300), load_sprite("asteroid.png",scale=True), (1, 0))
            Asteroid(self.utils.get_random_position(self.screen),self.append_asteroids ) for _ in range(NUMBER_ASTEROD)
        ]

    def append_bullet(self,bullet): #metodo logica per creare un bullet
        if len( self.bullets )>NUMBER_BULLET:
            self.bullets.remove(self.bullets[0])
        self.bullets .append(bullet)
        
    def append_asteroids(self,asteroid): #metodo per aggiungere un asteriode
        self.asteroids.append(asteroid)

    def main_loop(self): #loop per ogni clock
        while True:
            self._handle_input()
            self._process_game_logic()
            self._draw()
    def _init_pygame(self): #metodo di inizializzazione della libreria pygame
        pygame.init()
        pygame.display.set_caption("Space Rocks")

    def _handle_input(self): #gestore degli input (esci, muovi e spara)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                quit()
        #if (self.spaceship and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE ):
        #    self.spaceship.shoot()   
        is_key_pressed = pygame.key.get_pressed()
        if self.spaceship:
            if is_key_pressed[pygame.K_SPACE]:
                self.spaceship.shoot()
            if is_key_pressed[pygame.K_RIGHT]:
                self.spaceship.rotate(clockwise=True)
            elif is_key_pressed[pygame.K_LEFT]:
                self.spaceship.rotate(clockwise=False)
            if is_key_pressed[pygame.K_UP]:
                self.spaceship.accelerate()

    def _process_game_logic(self): #logiche di gioco (game over, game complete o sparo colpisce un asteiode)
        if self.spaceship:
            self.spaceship.move(self.screen) #self.spaceship.move()
        for game_object in self._get_game_objects(): #self.asteroid.moveSimple()
            game_object.move(self.screen)
        if self.spaceship:
            for asteroid in self.asteroids:
                if asteroid.collides_with(self.spaceship):
                    self.spaceship = None
                    self.message = "You lost!"# self.game_over()
                    break
        for bullet in self.bullets[:]:
            for asteroid in self.asteroids[:]:
                if asteroid.collides_with(bullet):
                    self.asteroids.remove(asteroid)
                    self.bullets.remove(bullet)
                    asteroid.split()
                    break
        for bullet in self.bullets[:]:
            if not self.screen.get_rect().collidepoint(bullet.position):
                self.bullets.remove(bullet)
        if not self.asteroids and self.spaceship:
            self.message = "You won!"

    def _draw(self): #metodo che ogni clock disegna gli oggetti
        self.screen.blit(self.background, (0, 0)) #self.screen.fill((0, 0, 255))
        #self.spaceship.draw(self.screen)
        for game_object in self._get_game_objects(): #self.asteroid.draw(self.screen)
            game_object.draw(self.screen) 
        if self.message:
            self.utils.print_text(self.screen, self.message, self.font)
        pygame.display.flip()
        self.clock.tick(60)

    def _get_game_objects(self): # metodo per ottenere gli oggetti in vita nel gioco
        game_objects = [*self.asteroids, *self.bullets]
        if self.spaceship:
            game_objects.append(self.spaceship)
        return game_objects
    
class GameUtils: #classe base con i metodi di utilita
    def load_sprite(self,name, with_alpha=True , scale = 0) : #metodo per caricare le immagini di un oggetto detto sprite
        path = f"/mnt/Dati/toDEL/{name}"
        if not os.path.exists(path):
            print ( f"File not exists {path}" )
        loaded_sprite = pygame.image.load(path) #from pygame.image import load
        if scale>0 :
            loaded_sprite = pygame.transform.smoothscale(loaded_sprite, (scale,scale ) )
        if with_alpha:
            return loaded_sprite.convert_alpha()
        else:
            return loaded_sprite.convert()
        
    def wrap_position(self,position, surface): # metodo per il calcolo di una posizione
        x, y = position
        w, h = surface.get_size()
        return Vector2(x % w, y % h)
    
    def get_random_position(self,surface): #metodo che genera la posizione random degli asteriodi
        return Vector2(
            random.randrange(surface.get_width()),
            random.randrange(surface.get_height()),
        )
    def get_random_velocity(self,min_speed, max_speed):
        speed = random.randint(min_speed, max_speed)
        angle = random.randrange(0, 360)
        return Vector2(speed, 0).rotate(angle)
    
    def print_text(self,surface, text, font, color=Color("tomato")): #metodo per il disegno di una scritta
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect()
        rect.center = Vector2(surface.get_size()) / 2
        surface.blit(text_surface, rect)

class GameObject: #classe di utilità per ogni oggetto (nave, asteriode, sparo)
    def __init__(self, position, sprite, velocity):
        self.utils=GameUtils()
        self.position = Vector2(position)
        self.sprite = sprite
        self.radius = sprite.get_width() / 2
        self.velocity = Vector2(velocity)
    def draw(self, surface):
        blit_position = self.position - Vector2(self.radius)
        surface.blit(self.sprite, blit_position)
    def moveSimple(self):
        self.position = self.position + self.velocity
    def move(self, surface):
        self.position = self.utils.wrap_position(self.position + self.velocity, surface)
    def collides_with(self, other_obj):
        distance = self.position.distance_to(other_obj.position)
        return distance < self.radius + other_obj.radius

class Spaceship(GameObject):
    MANEUVERABILITY = 5
    ACCELERATION = 0.05
    BULLET_SPEED = 2
    def __init__(self, position, create_bullet_callback):
        self.utils=GameUtils()
        self.create_bullet_callback = create_bullet_callback
        self.direction = Vector2(UP)
        super().__init__(position, self.utils.load_sprite("spaceship.png",scale=10), Vector2(0) )
    def rotate(self, clockwise=True):
        sign = 1 if clockwise else -1
        angle = self.MANEUVERABILITY * sign
        self.direction.rotate_ip(angle)
    def draw(self, surface):
        angle = self.direction.angle_to(UP)
        rotated_surface = rotozoom(self.sprite, angle, 1.0)
        rotated_surface_size = Vector2(rotated_surface.get_size())
        blit_position = self.position - rotated_surface_size * 0.5
        surface.blit(rotated_surface, blit_position)
    def accelerate(self):
        self.velocity += self.direction * self.ACCELERATION
    def shoot(self):
        bullet_velocity = self.direction * self.BULLET_SPEED + self.velocity
        bullet = Bullet(self.position, bullet_velocity)
        self.create_bullet_callback(bullet)
class Asteroid(GameObject):
    MIN_ASTEROID_DISTANCE = 250
    def __init__(self, position, create_asteroid_callback, size=3):
        self.utils=GameUtils()
        self.create_asteroid_callback = create_asteroid_callback
        self.size = size
        size_to_scale = {
            3: 1,
            2: 0.5,
            1: 0.25,
        }
        scale = size_to_scale[size]
        #sprite = rotozoom(load_sprite("asteroid"), 0, scale)
        super().__init__(position, self.utils.load_sprite("asteroid.png",scale=50*scale), self.utils.get_random_velocity(1, 3))
    def split(self):
        if self.size > 1:
            for _ in range(2):
                asteroid = Asteroid(self.position, self.create_asteroid_callback, self.size - 1)
                self.create_asteroid_callback(asteroid)
class Bullet(GameObject):
    def __init__(self, position, velocity):
        self.utils=GameUtils()
        super().__init__(position, self.utils.load_sprite("asteroid.png",scale=5), velocity)
    def move(self, surface):
        self.position = self.position + self.velocity

if __name__ == "__main__":
    space_rocks = SpaceRocks()
    space_rocks.main_loop()