# FROM "Python Simplified" https://www.youtube.com/watch?v=5qOnzF7RsNA

import tkinter as tk
from PIL import ImageTk #apt-get install python3-pil.imagetk

def load_frame2():
    print("hello")

#define window
root = tk.Tk()
root.title("Example1")

#position
#OLDroot.eval("tk::PlaceWindow . top")
x=root.winfo_screenwidth() // 6
y=int(root.winfo_screenheight() * 0.1)
root.geometry ('800x442+' + str(x) + "+" + str(y) ) #WIDTHxHEIGHT+TOP+LEFT

#red frame inside window 
frame1=tk.Frame(root,width=500,height=500,bg="#FF0000")
frame1.grid(row=0,column=0)
frame1.pack_propagate(False)

# logo image
logo_img=ImageTk.PhotoImage(file="/mnt/Dati/Foto.JPG")
logo_widget=tk.Label(frame1,image=logo_img)
logo_widget.image=logo_img
logo_widget.pack()

#simple label and button
lab=tk.Label(frame1,text="Ready fro your random number?",bg="green",fg="white") #font=("..",14)
lab.pack()
btn=tk.Button(frame1,text="Generate",bg="blue",fg="gold",cursor="hand2"
    ,activebackground="#badee2",command=lambda:load_frame2())
#lambda: needs to run more time in async mode and stop all at fist run
btn.pack()

#execute window
root.mainloop()

