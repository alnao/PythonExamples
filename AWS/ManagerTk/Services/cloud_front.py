from tkinter import *
import tkinter as tk
from  tkinter import ttk
#
class ConsoleCloudFront:

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
        self.lista_distribuzioni=service.list_distributions()# lista_distribuzioni,
        self.dettaglio_distribuzione=service.get_distribution #dettaglio_distribuzione,
        self.invalida_distribuzione=service.invalid_distribuzion #invalida_distribuzione,
        self.lista_invalidazioni=service.get_invalidations #lista_invalidazioni
        self.crea_window()

    def OLD__init__(self,frame,profilo,lista_distribuzioni,dettaglio_distribuzione,invalida_distribuzione,lista_invalidazioni,list_to_clipboard,reload_method):
        self.lista_distribuzioni=lista_distribuzioni
        self.profilo=profilo
        self.frame=frame
        self.distribuzione={}
        self.id=''
        self.dettaglio_distribuzione=dettaglio_distribuzione
        self.invalida_distribuzione=invalida_distribuzione
        self.lista_invalidazioni=lista_invalidazioni
        self.list_to_clipboard=list_to_clipboard
        self.reload_method=reload_method
        self.crea_window()

    def crea_window(self):
        #grid # https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        #grid see https://tkdocs.com/tutorial/grid.html
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
        self.tree['columns'] = ('Nome', 'Id', 'Stato')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=340)
        self.tree.column("Id",anchor=CENTER,width=130)
        self.tree.column("Stato",width=80)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Id",text="Id",anchor=CENTER)
        self.tree.heading("Stato",text="Stato",anchor=CENTER)
        i=1
        for dis in self.lista_distribuzioni:
            id=dis['Id']
            nome=dis['Origins']['Items'][0]['DomainName']
            stato=dis['Status']

            self.tree.insert(parent='',index='end',iid=i,text='',
                values=(nome,id,stato))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        id_distribuzione = self.tree.item(item)['values'][1]
        distribuzione={}
        nome=''
        stato=''
        for distribuzione_ciclo in self.lista_distribuzioni:
            if id_distribuzione==distribuzione_ciclo['Id']:
                distribuzione=distribuzione_ciclo
                stato=distribuzione['Status']
                nome=distribuzione['Origins']['Items'][0]['DomainName']
        self.distribuzione=distribuzione
        self.id=id_distribuzione
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        #Label(self.frame2, text="Id: " + id_distribuzione ).pack()
        #Label(self.frame2, text="Stato: " + stato ).pack()
        #Label(self.frame2, text="Nome: " + nome ).pack()

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
        for key in distribuzione:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,distribuzione[key]) )
            i=i+1
        self.tree2.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree2,1) )
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2,height=200)
        l_name= Label(self.frame2b, text="Origine")
        l_name.pack()
        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=5)
        self.tree3['columns'] = ('Chiave', 'Valore')
        self.tree3.column("#0", width=0,  stretch=NO)
        self.tree3.column("Chiave", width=200)
        self.tree3.column("Valore",anchor=CENTER,width=480)
        self.tree3.heading("#0",text="",anchor=CENTER)
        self.tree3.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree3.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        for valore in distribuzione['Origins']['Items'][0]:
            self.tree3.insert(parent='',index='end',iid=i,text='',
                    #values=( str(valore['Key']),str(valore['Value'])) )
                values=( str(valore),distribuzione['Origins']['Items'][0][valore]) )
            i=i+1
        self.tree3.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3,1) )
        self.tree3.pack()
        self.frame2a.pack()
        self.frame2b.pack()
#INVALIDA
        li=self.lista_invalidazioni(id_distribuzione)
        self.frame2i = ttk.Frame(self.frame2,height=200)
        l_namei= Label(self.frame2i, text="Invalidations (click here to invalidate)") 
        l_namei.bind("<Button-1>", func = lambda event :self.run_invalidation(id_distribuzione) )
        l_namei.pack()
#TODO click to invalidare
        #l_name.bind("<Button-1>", lambda e:self.open_window_set_tag())
        self.scroll2i = Scrollbar(self.frame2i)
        self.scroll2i.pack(side=RIGHT, fill=Y)
        self.tree3i = ttk.Treeview(self.frame2i,yscrollcommand=self.scroll2i.set,height=5)
        self.tree3i['columns'] = ('Chiave', 'Valore')
        self.tree3i.column("#0", width=0,  stretch=NO)
        self.tree3i.column("Chiave", width=200)
        self.tree3i.column("Valore",anchor=CENTER,width=480)
        self.tree3i.heading("#0",text="",anchor=CENTER)
        self.tree3i.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree3i.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        for eli in li:
            self.tree3i.insert(parent='',index='end',iid=i,text='',
                    #values=( str(valore['Key']),str(valore['Value'])) )
                values=( eli['Status'], eli['CreateTime'] ) )
            i=i+1
        self.tree3i.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3i,1) )
        self.tree3i.pack()

        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2i.pack()
        self.frame2.pack(side=LEFT)

    def run_invalidation(self, id_distribuzione):
        self.invalida_distribuzione(id_distribuzione)
        self.reload_method()

if __name__ == '__main__':
    print("Error")