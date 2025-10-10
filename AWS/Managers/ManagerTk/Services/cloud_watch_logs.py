from tkinter import *
import tkinter as tk
from  tkinter import ttk
from datetime import datetime
import json

class ConsoleCloudWatchLogs:

    def __init__(self,frame,profilo,configuration,classe_sdk,list_to_clipboard):
        for widget in frame.winfo_children():
            widget.destroy()
        self.configuration=configuration
        self.profilo=profilo
        self.frame=frame
        self.classe_sdk=classe_sdk
        self.list_to_clipboard=list_to_clipboard
        self.lista_o1=[]
        self.load_frame()
        self.reload_method=self.load_frame
        
    def load_frame(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        service=self.classe_sdk(self.profilo)
        self.list=service.list_log_groups()
        self.list = sorted( self.list , key=lambda tup: tup["logGroupName"] , reverse=False )
        self.list_log_streams=service.list_log_streams
        self.get_log_events=service.get_log_events
        self.crea_window()

    def crea_window(self):
        self.frame.columnconfigure(2)
        self.frame1 = ttk.Frame(self.frame, width=550, height=630)
        self.frame1.grid(row = 1, column = 2, sticky = tk.W, padx = 2) 
        self.frame1.pack(side=LEFT, expand = 1)
        self.frame2 = ttk.Frame(self.frame, width=650, height=630)
        self.frame2.grid(row = 1, column = 2, sticky = tk.E, padx = 2) 
        self.frame2.pack(side=LEFT, expand = 1)
        self.scroll = Scrollbar(self.frame1)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=30)
        self.tree['columns'] = ('Nome')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=350)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        i=1
        for dis in self.list:
            self.tree.insert(parent='',index='end',iid=i,text='',
                values=dis['logGroupName'])
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        self.el_selezionata=self.tree.item(item)['values'][0]
        
        self.free2b_loaded=False
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="Log: " + self.el_selezionata ).pack()
        
        self.lista_stream=self.list_log_streams( self.el_selezionata )
        self.lista_stream = sorted( self.lista_stream , key=lambda tup: tup["creationTime"] , reverse=True )
        self.frame2a = ttk.Frame(self.frame2,height=500)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=10)
        self.tree2['columns'] = ('Time', 'Valore')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Time", width=200)
        self.tree2.column("Valore",anchor=CENTER,width=600)
        self.tree2.heading("#0",text="",anchor=CENTER)
        self.tree2.heading("Time",text="CreationTime",anchor=CENTER)
        self.tree2.heading("Valore",text="Valore",anchor=CENTER)
        i=0


        for key in self.lista_stream:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(  
                        str(datetime.fromtimestamp( key['creationTime'] /1000 ) ),
                        str(key['logStreamName'])
                    )
            )
            i=i+1
        self.tree2.bind("<Double-1>", self.show_logs)
        self.tree2.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree2,1) )
        self.tree2.pack()
        if self.free2b_loaded==True:
            self.frame2b.pack_forget() # or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.tree3.pack_forget()
            self.free2b_loaded==False
            self.tree3.pack()
        self.frame2b = ttk.Frame(self.frame2)
        self.frame2b.pack()
        self.frame2a.pack()        
        self.frame2.pack(side=LEFT)

    def show_logs(self,event):
        if self.free2b_loaded==True:
            self.frame2b.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
        self.frame2b = ttk.Frame(self.frame2)
        self.free2b_loaded=True
        item = self.tree2.selection()[0]
        self.el_selezionata_stream=self.tree2.item(item)['values'][1]
        self.lista_logs = self.get_log_events( self.el_selezionata , self.el_selezionata_stream )
        self.lista_logs = self.lista_logs['events']
        self.lista_logs = sorted( self.lista_logs , key=lambda tup: tup["timestamp"] , reverse=True )
        l_name= Label(self.frame2b, text="Logs stream: " +  self.el_selezionata_stream )
        l_name.pack()
        l_name.bind("<Button-1>", lambda e:self.open_window_set_tag())
        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=15)
        self.tree3['columns'] = ('TimeStamp', 'Message')
        self.tree3.column("#0", width=0,  stretch=NO)
        self.tree3.column("TimeStamp", width=200)
        self.tree3.column("Message",width=600)
        self.tree3.heading("#0",text="",anchor=CENTER)
        self.tree3.heading("TimeStamp",text="TimeStamp",anchor=CENTER)
        self.tree3.heading("Message",text="Message",anchor=CENTER)
        i=0
        for es in self.lista_logs:
            self.tree3.insert(parent='',index='end',iid=i,text='',
                    values=(
                        str(datetime.fromtimestamp( es['timestamp'] /1000 ) )
                        , es['message']
                    )) 
            i=i+1
        self.tree3.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3,0) )
        self.tree3.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)