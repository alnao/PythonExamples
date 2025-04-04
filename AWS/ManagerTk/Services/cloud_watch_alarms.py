from tkinter import *
import tkinter as tk
from  tkinter import ttk
import json

class ConsoleCloudWatchAlarms:

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
        self.list=service.list_alarms()
        self.get_alarm_history=service.get_alarm_history
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
        self.tree['columns'] = ('Nome', 'Info')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=200)
        self.tree.column("Info",width=150)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Info",text="Info",anchor=CENTER)
        i=1
        for dis in self.list:
            nome=dis['AlarmName']
            info=str(dis['StateValue'])
            self.tree.insert(parent='',index='end',iid=i,text='',
                values=(nome,info))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        selezionato_id = self.tree.item(item)['values'][0]
        selezionato={}
        for elemento in self.list:
            if selezionato_id==elemento['AlarmName']:
                selezionato=elemento
        self.selezionato=selezionato
        self.selezionato_id=selezionato_id
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        #Label(self.frame2, text="Id: " + selezionato_id ).pack()
        Label(self.frame2, text="Nome: " + elemento['AlarmName'] ).pack()
        #Label(self.frame2, text="(doppio click sulla risorsa per copiare l'url)" ).pack()

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
        for key in self.selezionato:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,self.selezionato[key]) )
            i=i+1
        self.tree2.bind("<Double-1>", self.copy_value2)
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2,height=300)
        #servizi get_alarm_history
        detail_ob = self.get_alarm_history(self.selezionato_id)
        if len(detail_ob)>0:
            l_name= Label(self.frame2b, text="Instances")
            l_name.pack()
            self.scroll2b = Scrollbar(self.frame2b)
            self.scroll2b.pack(side=RIGHT, fill=Y)
            self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=10)
            self.tree3['columns'] = ('Timestamp','HistorySummary', 'oldState', 'newState')
            self.tree3.column("#0", width=0,  stretch=NO)
            self.tree3.column("Timestamp", width=200)
            self.tree3.column("HistorySummary", width=200)
            self.tree3.column("oldState",anchor=CENTER,width=200)
            self.tree3.column("newState",anchor=CENTER,width=200)
            self.tree3.heading("#0",text="",anchor=CENTER)
            self.tree3.heading("Timestamp",text="Timestamp",anchor=CENTER)
            self.tree3.heading("HistorySummary",text="HistorySummary",anchor=CENTER)
            self.tree3.heading("oldState",text="oldState",anchor=CENTER)
            self.tree3.heading("newState",text="newState",anchor=CENTER)
            i=0
            for event in detail_ob:
                history = json.loads( event['HistoryData'] )
                oldState=""
                if 'oldState' in history:
                    oldState=history['oldState']
                newState=""
                if 'newState' in history:
                    newState=history['newState']
                self.tree3.insert(parent='',index='end',iid=i,text='',
                    #values=( str(valore['Key']),str(valore['Value'])) )
                    values=( str(event['Timestamp']), str(event['HistorySummary']) 
                        , oldState
                        , newState
                    )
                )
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