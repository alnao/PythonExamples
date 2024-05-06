import os
import random
import string
import time

#simple games from https://www.youtube.com/watch?v=3kdM9wyglnw

def play_game():
    os.system("cls||clear")

    print ("VITAL MESSAGE \n")

    while True:
        D=int ( input ("INSERT DIFFICULTY (4-10):") )
        if D>=4 and D<=10 :
            break


    M=""
    for i in range(D):
        M += random.choice(string.ascii_letters)

    os.system("cls||clear")

    print ("SEND MESSAGE \n \n ",M)
    time.sleep(0.5 * D)

    os.system("cls||clear")
    N=input("INSERT MESSAGE:")

    os.system("cls||clear")
    if M==N:
        print("MESSAGE CORRECT")
    else:
        print("MESSAGE INCORRECT")


if __name__ == "__main__":
    play_game()