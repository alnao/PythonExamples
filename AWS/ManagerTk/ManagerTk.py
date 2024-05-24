import tkinter as tk
import os
import sys
import yaml #pip install pyyaml
from tkinter import *
from tkinter import ttk
from Services.services import ServiceManager
from Application.menu import ConsoleMenu,StatusBar

#see example tk https://realpython.com/python-gui-tkinter/

class AwsPyConsole:
    larghezza=1500
    altezza=700
    def __init__(self,configuration):
        self.service_manager= ServiceManager(self)

        self.profilo='default'
        self.root = tk.Tk()
        self.configuration=configuration
        # Create window
        self.root.title('Aws Py Console')
        x=0 #ex 10 ex root.winfo_screenwidth() // 6
        y=0 #ex 10 ex int(root.winfo_screenheight() * 0.1)
        self.root.geometry (''+str(self.larghezza)+'x'+str(self.altezza+30)+'+' + str(x) + "+" + str(y) ) #WIDTHxHEIGHT+TOP+LEFT
        #get AWS profiles           #self.aws_profiles=AwsProfilesSdk()
        self.lista_profili_aws=self.service_manager.get_lista_profili()
        #crete menu
        ConsoleMenu(self.root,self.lista_profili_aws,self.load_profile)
        if len(self.lista_profili_aws)>0:
            self.load_profile( self.root, self.lista_profili_aws[0] )
        self.root.mainloop()

    def list_to_clipboard(self, list, index):
        item = str ( list.selection()[0] )
        text = list.item(item)['values'][index]
        self.root.clipboard_clear()
        self.root.clipboard_append(str(text))
        self.status.set( str(text) )

    def add_text_to_frame(self,frame,text):
        Label(frame, text=text).pack()
        frame.pack_propagate(False)

    def main_frame(self,root,profilo): #nota: funziona solo se c'è un iframe nella main
        self.profilo=profilo
        if self.profilo=="": #nessun profilo selezionato dal menu
            self.frame1=tk.Frame(root,width=self.larghezza-24,height=self.altezza-24,bg="#EEEEEE")
            self.frame1.grid(row=0,column=0)
            self.add_text_to_frame(self.frame1,"Selezionare un profilo") # Label(frame1, text="Selezionare un profilo").pack()
            #frame1.pack_propagate(False)
            return
        self.frame1=tk.Frame(root,width=self.larghezza-25,height=self.altezza-25,bg="#EEEEEE")
        self.status = StatusBar(self.frame1, self.profilo)
        self.frame1.grid(row=0,column=0)
        #tabs window
        self.tabs = ttk.Notebook(self.frame1, width=self.larghezza-30, height=self.altezza-30)
        self.tabs.pack(fill=BOTH, expand=TRUE)
        #TABS 
        for e in self.service_manager.get_lista_funzionalita():
            e_frame= ttk.Frame(self.tabs)
            self.tabs.add(e_frame , text=e['title'] ) 
            self.add_text_to_frame(e_frame,e['desc']+ " del profilo " + self.profilo) 
            if e['automatic']==True:
                e['metodo'](frame=e_frame) 
            else:
                b=Button(e_frame, text = "Load service " + e['desc'] )# ,bd=5,fg="blue",font="calibre 18 bold", pady=15 )
                #function= lambda method=e['metodo']: lambda frame=e_frame: method(frame)
                #b.bind("<Button-1>", lambda ev: function(e['metodo'])(e_frame) )
                #nota:le lambda non funzionano nei cicli quindi fatto così: https://www.youtube.com/watch?v=fZE6ZWde-Os
                b.bind("<Button-1>", self.lambda_tab_loader(e,e_frame) ) #lambda ev: function(e['metodo'])(e_frame) )
                b.pack() #side=LEFT
            self.tabs.pack(expand=1, fill="both")

    def lambda_tab_loader(self,funzionalita,frame): 
        #nota:le lambda non funzionano nei cicli quindi fatto così: https://www.youtube.com/watch?v=fZE6ZWde-Os
        def method():
            for widget in frame.winfo_children():
                widget.destroy()
            funzionalita['metodo'](frame)
        return lambda ev:method()

    #PROFILEs
    def load_profile(self,root,profilo):
        self.profile_name=profilo
        #boto3.setup_default_session(profile_name=self.profile_name)
        #boto3.Session(profile_name=self.profile_name,sso_start_url="https://bancotrevenezie.awsapps.com/start", sso_region='eu-west-1')
        self.service_manager.set_active_profile( profilo ) #self.aws_profiles.set_active_profile( profilo )
        self.main_frame(root,self.profile_name)
        self.root.title('Aws Py Console - profilo attivo: ' + profilo)

if __name__ == '__main__':
    configuration={}
    if os.path.exists("./config.yaml"):
        configuration=yaml.safe_load(open("./config.yaml"))
    if os.path.exists("C:\\temp\\configConsole.yaml"):
        configuration=yaml.safe_load(open("C:\\temp\\configConsole.yaml"))
    p=AwsPyConsole(configuration)

""" Esempio di file yaml di configurazione
default:
  s3:
  - label: alberto incoming
    bucket: alberto-input
    path: INCOMING
  - label: alberto outgoing
    bucket: alberto-input
    path: OUTGOING
  - label: sftp-simulator
    bucket: formazione-sftp-simulator
    path: ''
"""