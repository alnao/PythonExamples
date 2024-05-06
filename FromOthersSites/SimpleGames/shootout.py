from time import sleep
from random import randint
import os

#simple games from https://www.youtube.com/watch?v=3kdM9wyglnw

#DON'T WORK
#try: #ßee https://stackoverflow.com/questions/38172907/ubuntu-equivalent-to-getch-function-from-msvcrt
#    import getch as lib #import getch, getche         # Linux
#except ImportError:
#    import msvcrt as lib # import getch, getche        # Windows

#DON'T WORK
#import sys #https://code.activestate.com/recipes/572182-how-to-implement-kbhit-on-linux/
#from select import select
#def kbhit():
#    dr,dw,de = select([sys.stdin], [], [], 0)
#    print("kbhit",dr)
#    return dr != []



import os

#see https://www.mail-archive.com/linux-il@cs.huji.ac.il/msg66473.html
if os.name == 'nt':  # Windows
    os_ = 'nt'
    import msvcrt
else:                # Posix (Linux, OS X)
    os_ = 'LINUX'
    import sys
    import termios
    import atexit
    from select import select
ENTER = 10
ESC = 27
BACKSPACE = 127
TAB = 9
class KBHit:
    """ this class does the work """    
    def __init__(self):
        """Creates a KBHit object to get keyboard input """

        if os_ == 'LINUX':
            # Save the terminal settings
            self.fd = sys.stdin.fileno()
            self.new_term = termios.tcgetattr(self.fd)
            self.old_term = termios.tcgetattr(self.fd)
    
            # New terminal setting unbuffered
            self.new_term[3] = (self.new_term[3] & ~termios.ICANON & ~termios.ECHO)
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.new_term)
    
            # Support normal-terminal reset at exit
            atexit.register(self.set_normal_term)
    
    
    def set_normal_term(self):
        """ Resets to normal terminal.  On Windows does nothing """
        if os_ == 'LINUX':
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)


    def getch(self):
        """ Returns a keyboard character after kbhit() has been called """
        if os_ == 'nt':
            return msvcrt.getch().decode('utf-8')
        else:
            return sys.stdin.read(1)

    def kbhit(self):
        """ Returns True if keyboard character was hit, False otherwise. """
        if os_ == 'nt':
            return msvcrt.kbhit()
        else:
            dr, dw, de = select([sys.stdin], [], [], 0)
            return dr != []
    
def test_KBHit():
    """ main() tests the kbhit() and getch() functions """
    kbd = KBHit()
    print ('Hit any key, or ESC to exit')

    while True:
        if kbd.kbhit():
            print ("HIT ",)
            char_hit = kbd.getch()
            if ord(char_hit) == ESC:
                print ("ESC - ending test")
                break
            print (char_hit, ord(char_hit))
             
    kbd.set_normal_term()

def play_game(): 
    os.system("cls||clear")
    print("PARATORIA - COWBOYS SHOOTOUT") 
    print("You're back to back, take 10 paces and ... ")

    W=1
    while W<=10:
        sleep(0.5)
        print (W , "..." , "\n")
        W+=1

    kbd = KBHit()

    S=randint(1,5)
    sleep(5)

    if kbd.kbhit() == True: #ex lib.kbhit()
        os.system("cls||clear")
        print("YOU SHOOT FIRST")
        sleep(0.5)
        #exit()
    else:
        print ("HE DRAWS...")
        sleep(0.5)
        print ("YOU DIE")

if __name__ == "__main__":
    play_game()