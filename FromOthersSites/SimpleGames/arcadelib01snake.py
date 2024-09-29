# see https://www.geeksforgeeks.org/python-arcade-player-movement/

# Importing arcade module 
import arcade 
  
# Creating MainGame class        
class MainGame(arcade.Window): 
    def __init__(self): 
        super().__init__(600, 600, title="Player Movement") 
  
        # Initializing the initial x and y coordinated 
        self.x = 250 
        self.y = 250
  
        # Initializing a variable to store 
        # the velocity of the player 
        self.vel_x = 0
        self.vel_y = 0
  
    # Creating on_draw() function to draw on the screen 
    def on_draw(self): 
        arcade.start_render() 
  
        # Drawing the rectangle using 
        # draw_rectangle_filled function 
        arcade.draw_rectangle_filled(self.x, self.y,50, 50, 
                                     arcade.color.GREEN ) 
    # Creating on_update function to 
    # update the x coordinate 
    def on_update(self,delta_time): 
        self.x += self.vel_x * delta_time 
        self.y += self.vel_y * delta_time 
  
          
    # Creating function to change the velocity 
    # when button is pressed 
    def on_key_press(self, symbol,modifier): 
  
        # Checking the button pressed 
        # and changing the value of velocity 
        if symbol == arcade.key.UP: 
            self.vel_y = 300
        elif symbol == arcade.key.DOWN: 
            self.vel_y = -300
        elif symbol == arcade.key.LEFT: 
            self.vel_x = -300
        elif symbol == arcade.key.RIGHT: 
            self.vel_x = 300
  
    # Creating function to change the velocity 
    # when button is released 
    def on_key_release(self, symbol, modifier): 
  
        # Checking the button released 
        # and changing the value of velocity 
        if symbol == arcade.key.UP: 
            self.vel_y = 0
        elif symbol == arcade.key.DOWN: 
            self.vel_y = 0
        elif symbol == arcade.key.LEFT: 
            self.vel_x = 0
        elif symbol == arcade.key.RIGHT: 
            self.vel_x = 0
          
          
# Calling MainGame class        
MainGame() 
arcade.run() 