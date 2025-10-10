from tkinter import *
import tkinter as tk
from  tkinter import ttk
import json
import sys
import os
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from Application.json_viewer import JSONViewer

class ConsoleRds:
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
        self.lista_db=service.db_instances_list()
        self.lista_db = sorted(self.lista_db, key=lambda tup: tup["DBInstanceIdentifier"])
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
        self.tree['columns'] = ('Nome', 'Engine', 'Stato')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=340)
        self.tree.column("Engine",anchor=CENTER,width=130)
        self.tree.column("Stato",width=80)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Engine",text="Engine",anchor=CENTER)
        self.tree.heading("Stato",text="Stato",anchor=CENTER)
        i=1
        for dis in self.lista_db:
            id=dis['DBInstanceIdentifier']
            tipo=dis['Engine']
            stato=dis['DBInstanceStatus']
            self.tree.insert(parent='',index='end',iid=i,text='',
                values=(id,tipo,stato))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        id_db = self.tree.item(item)['values'][0]
        istanza_db={}
        db_class=''
        stato=''
        for istanza_db_ciclo in self.lista_db:
            if id_db==istanza_db_ciclo['DBInstanceIdentifier']:
                istanza_db=istanza_db_ciclo
                stato=istanza_db['DBInstanceStatus']
                db_class=istanza_db['DBInstanceClass']
        self.istanza_db=istanza_db
        self.id=id_db
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="Id: " + id_db ).pack()
        Label(self.frame2, text="Stato: " + stato ).pack()
        Label(self.frame2, text="Classe: " + db_class ).pack()

        self.frame2a = ttk.Frame(self.frame2,height=100)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=15)
        self.tree2['columns'] = ('Chiave', 'Valore')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Chiave", width=200)
        self.tree2.column("Valore",anchor=CENTER,width=480)
        self.tree2.heading("#0",text="",anchor=CENTER)
        self.tree2.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree2.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        for key in istanza_db:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,istanza_db[key]) )
            i=i+1
        self.tree2.bind("<Double-1>", self.copy_value2)
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2,height=300)
        if 'Endpoint' in istanza_db:
            l_name= Label(self.frame2b, text="Endpoint")
            l_name.pack()
            self.scroll2b = Scrollbar(self.frame2b)
            self.scroll2b.pack(side=RIGHT, fill=Y)
            self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=10)
            self.tree3['columns'] = ('Chiave', 'Valore')
            self.tree3.column("#0", width=0,  stretch=NO)
            self.tree3.column("Chiave", width=200)
            self.tree3.column("Valore",anchor=CENTER,width=480)
            self.tree3.heading("#0",text="",anchor=CENTER)
            self.tree3.heading("Chiave",text="Chiave",anchor=CENTER)
            self.tree3.heading("Valore",text="Valore",anchor=CENTER)
            i=0
            for valore in istanza_db['Endpoint']:
                self.tree3.insert(parent='',index='end',iid=i,text='',
                        #values=( str(valore['Key']),str(valore['Value'])) )
                    values=( str(valore),istanza_db['Endpoint'][valore]) )
                i=i+1
            self.tree3.bind("<Double-1>", self.copy_value3)
            self.tree3.pack()
        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)

    def copy_value2(self, event):
        self.to_clipboard(self.tree2,1)
    def copy_value3(self, event):
        self.to_clipboard(self.tree3,1)

if __name__ == '__main__':
    print("Error")