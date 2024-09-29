
#see https://realpython.com/arcade-python-game-framework/

import arcade
import os 
import random
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Arcade Space Shooter"
SCALING = 2.0
DIR_PATH=file_path = os.path.dirname(os.path.abspath(__file__))+"/"

class FlyingSprite(arcade.Sprite): #Base class for all flying sprites Flying sprites include enemies and clouds
    def update(self):
        super().update()
        if self.right < 0:
            self.remove_from_sprite_lists()

class SpaceShooter(arcade.Window):
    
    def __init__(self, width, height, title):
        super().__init__(width, height, title)
        self.enemies_list = arcade.SpriteList()
        self.clouds_list = arcade.SpriteList()
        self.all_sprites = arcade.SpriteList()
        arcade.set_background_color(arcade.color.SKY_BLUE)
        self.paused=False

    def on_draw(self):
        self.clear() # 
        #arcade.draw_lrtb_rectangle_filled(5, 35, 590, 570, arcade.color.BITTER_LIME)
        self.all_sprites.draw()
        #arcade.finish_render()
        output = f"Sprite Count: {self.all_sprites.__len__}"
        arcade.draw_text(output,
                         20,
                         SCREEN_WIDTH - 20 ,
                         arcade.color.BLACK, 16)

    def setup(self):
        self.player = arcade.Sprite(DIR_PATH + "images/jet.png", SCALING)
        self.player.width = 20
        self.player.height = 20
        self.player.center_y = self.height / 2
        self.player.left = 10
        self.all_sprites.append(self.player)
        arcade.schedule(self.add_enemy, 0.25)
        arcade.schedule(self.add_cloud, 1.0)

    def add_enemy(self, delta_time: float):
        enemy = FlyingSprite(DIR_PATH + "images/missile.png", SCALING)
        enemy.width = 10
        enemy.height = 10
        enemy.left = random.randint(self.width, self.width+80 )
        enemy.top = random.randint(10, self.height - 10)
        enemy.velocity = (random.uniform(-1, -.1), 0)#-20,-5
        self.enemies_list.append(enemy)
        self.all_sprites.append(enemy)
    def add_cloud(self, delta_time: float):
        cloud = FlyingSprite(DIR_PATH + "images/cloud.png", SCALING)
        cloud.width = 10
        cloud.height = 10        
        cloud.left = random.randint(self.width, self.width+80 )
        cloud.top = random.randint(10, self.height - 10)
        cloud.velocity = (random.uniform(-1, -.1), 0) #-5,-2
        self.clouds_list.append(cloud)
        self.all_sprites.append(cloud)
    def on_update(self, delta_time: float):
        if self.paused:
            return
        # Did you hit anything? If so, end the game
        if self.player.collides_with_list(self.enemies_list):
            arcade.close_window()
        self.all_sprites.update()
        #return super().on_update(delta_time)
        if self.player.top > self.height:
            self.player.top = self.height
        if self.player.right > self.width:
            self.player.right = self.width
        if self.player.bottom < 0:
            self.player.bottom = 0
        if self.player.left < 0:
            self.player.left = 0

    def on_key_press(self, symbol, modifiers):
        """Handle user keyboard input
        Q: Quit the game
        P: Pause/Unpause the game
        I/J/K/L: Move Up, Left, Down, Right
        Arrows: Move Up, Left, Down, Right

        Arguments:
            symbol {int} -- Which key was pressed
            modifiers {int} -- Which modifiers were pressed
        """
        if symbol == arcade.key.Q:
            # Quit immediately
            arcade.close_window()

        if symbol == arcade.key.P:
            self.paused = not self.paused

        if symbol == arcade.key.I or symbol == arcade.key.UP:
            self.player.change_y = 5

        if symbol == arcade.key.K or symbol == arcade.key.DOWN:
            self.player.change_y = -5

        if symbol == arcade.key.J or symbol == arcade.key.LEFT:
            self.player.change_x = -5

        if symbol == arcade.key.L or symbol == arcade.key.RIGHT:
            self.player.change_x = 5

    def on_key_release(self, symbol: int, modifiers: int):
        if (
            symbol == arcade.key.I
            or symbol == arcade.key.K
            or symbol == arcade.key.UP
            or symbol == arcade.key.DOWN
        ):
            self.player.change_y = 0

        if (
            symbol == arcade.key.J
            or symbol == arcade.key.L
            or symbol == arcade.key.LEFT
            or symbol == arcade.key.RIGHT
        ):
            self.player.change_x = 0

# Main code entry point
if __name__ == "__main__":
    os.chdir(DIR_PATH)
    app = SpaceShooter(SCREEN_WIDTH,SCREEN_HEIGHT,SCREEN_TITLE)
    app.setup()
    arcade.run()