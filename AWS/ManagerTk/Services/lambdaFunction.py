from tkinter import *
import tkinter as tk
from datetime import datetime
from  tkinter import ttk

class ConsoleLambda:
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
        self.lista_lambda=service.list_functions()
        self.lista_lambda = sorted(self.lista_lambda, key=lambda tup: tup["Name"])
        self.dettaglio_lambda=service.get_function
        self.statistiche=service.get_statistic
        self.logs=service.get_logs
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
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=50)
        self.tree['columns'] = ( 'Name', 'RunTime')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Name",width=350)
        self.tree.column("RunTime",anchor=CENTER,width=100)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Name",text="Name",anchor=CENTER)
        self.tree.heading("RunTime",text="RunTime",anchor=CENTER)
        i=1
        for lam in self.lista_lambda:
            self.tree.insert(parent='',index='end',iid=i,text='',
                values=(lam['Name'],lam['RunTime']))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab


    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        self.lambda_sel = self.tree.item(item)['values'][0]
        lambda_detail=self.dettaglio_lambda(self.lambda_sel)
        lambda_stat=self.statistiche(self.lambda_sel)
        lambda_stat = sorted(lambda_stat, key=lambda tup: tup["Timestamp"])
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        l=Label(self.frame2, text="Lambda: " + self.lambda_sel )
        l.bind("<Button-1>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        l.pack()
        #Button(self.frame2, text = "Stop", command=self.send_stop).pack()
        #Label(self.frame2, text="Nome: " + nome ).pack()
        self.frame2a = ttk.Frame(self.frame2,height=300)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=20)
        self.tree2['columns'] = ('Chiave', 'Valore')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Chiave", width=200)
        self.tree2.column("Valore",anchor=CENTER,width=480)
        self.tree2.heading("#0",text="",anchor=CENTER)
        self.tree2.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree2.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        for key in lambda_detail:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,lambda_detail[key]) )
            i=i+1
        self.tree2.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree2,1) )
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2)
        
        l_name= Label(self.frame2b, text="Statistiche Esecuzione (click here to logs)")
        l_name.pack()
        l_name.bind("<Button-1>", lambda e:self.open_window_logs())
        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=5)
        self.tree3['columns'] = ('Chiave', 'Valore')
        self.tree3.column("#0", width=0,  stretch=NO)
        self.tree3.column("Chiave", width=200)
        self.tree3.column("Valore",anchor=CENTER,width=480)
        self.tree3.heading("#0",text="",anchor=CENTER)
        self.tree3.heading("Chiave",text="Timestamp",anchor=CENTER)
        self.tree3.heading("Valore",text="SampleCount",anchor=CENTER)
        i=0
        for s in lambda_stat:
            self.tree3.insert(parent='',index='end',iid=i,text='',
                    values=(s['Timestamp'],s['SampleCount']) )
            i=i+1
        #self.tree3.bind("<Double-1>", self.open_detail_tag)
        self.tree3.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3,1) )
        self.tree3.pack()
        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)

    def open_window_logs(self):
        w_child=Toplevel(self.frame) # Child window 
        w_child.geometry("1000x600")#+ str(x) + "+" + str(y))  # Size of the window 
        w_child.title("Logs of " + self.lambda_sel)
        self.frame4 = ttk.Frame(w_child)
        self.tree4 = ttk.Treeview(self.frame4,yscrollcommand=self.scroll2b.set,height=55)
        self.tree4['columns'] = ('TS', 'Message')
        self.tree4.column("#0", width=0,  stretch=NO)
        self.tree4.column("TS", width=120)
        self.tree4.column("Message",width=800)
        self.tree4.heading("#0",text="",anchor=CENTER)
        self.tree4.heading("TS",text="Timestamp",anchor=CENTER)
        self.tree4.heading("Message",text="Message",anchor=CENTER)
        i=0
        lambda_logs=self.logs(self.lambda_sel)
        lambda_logs = sorted(lambda_logs, key=lambda tup: tup["timestamp"])
        for s in lambda_logs:
            my_date=datetime.fromtimestamp( s['timestamp'] /1000 ) #https://stackoverflow.com/questions/65063058/convert-unix-timestamp-to-date-string-with-format-yyyy-mm-dd
            self.tree4.insert(parent='',index='end',iid=i,text='',
                values=( my_date.strftime("%Y-%m-%d %H:%M:%S") ,s['message']) )
            i=i+1
        #self.tree3.bind("<Double-1>", self.open_detail_tag)
        self.tree4.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree4,1) )
        self.tree4.pack()
        self.frame4.pack()
        w_child.focus()
        w_child.grab_set()