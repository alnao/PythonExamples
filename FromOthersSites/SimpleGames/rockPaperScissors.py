#simple from https://www.youtube.com/watch?v=1SP5m9X4hF8
from enum import Enum
import random

class Shape(Enum):
    ROCK="Rock"
    PAPER="Paper"
    SCISSOR="Scissor"

class Player():
    def __init__(self,name):
        self.score=0
        self.name=name
    def choose(self):
        while True:
            user_input=input(self.name + " please insert : ")
            if (user_input not in [Shape.PAPER.value,Shape.ROCK.value,Shape.SCISSOR.value]):
                print("Invalid option. Please try again (Rock,Paper,Scissor)")
            else: 
                return user_input
        

class Computer(Player):
    def choose(self):
        self.choice=random.choice([Shape.PAPER.value,Shape.ROCK.value,Shape.SCISSOR.value])
        return self.choice
        

class Game():
    def __init__(self):
        self.max_round=3;
        self.round=0
        self.player1=None
        self.player2=None

    def start_game(self,name1,name2):
        self.player1=Player(name1)
        self.player2=Computer(name2)
        print ("------ START GAME ------")
    
    def play(self):
        while (self.round < self.max_round):
            self.calculate_scores( self.player1.choose() , self.player2.choose() )
            #print ("Round" , self.round)
    def end(self):
        print ("------ END GAME ------")
        if self.player1.score > self.player2.score:
            print("Player 1 WINS")
        else:
            print("Player 2 WINS")
    
    def calculate_scores(self,player1_choice,player2_choice):
        print ("Round" , self.round , " Player 1=" , player1_choice, " Player 2=" , player2_choice )
        if (player1_choice==player2_choice):
            print(" - Round deuce")
            return 0
        if (player1_choice == Shape.ROCK.value and player2_choice == Shape.SCISSOR.value or \
            player1_choice == Shape.PAPER.value and player2_choice == Shape.ROCK.value or \
            player1_choice == Shape.SCISSOR.value and player2_choice == Shape.PAPER.value):
            self.player1.score=self.player1.score+1
            self.round +=1
            print(" - Player 1 win ROUND ")
            return 1
        if (player2_choice == Shape.ROCK.value and player1_choice == Shape.SCISSOR.value or \
            player2_choice == Shape.PAPER.value and player1_choice == Shape.ROCK.value or \
            player2_choice == Shape.SCISSOR.value and player1_choice == Shape.PAPER.value):
            self.player2.score=self.player2.score+1
            self.round +=1
            print(" - Player 2 win ROUND ")
            return 2
        print(" - None wins")
        return 0



if __name__=="__main__":
    game=Game()
    game.start_game("Alberto","Computer")
    game.play()
    game.end()