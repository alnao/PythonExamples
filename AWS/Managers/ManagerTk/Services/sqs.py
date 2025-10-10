from tkinter import *
import tkinter as tk
from  tkinter import ttk
import json
import sys
import os
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from Application.json_viewer import JSONViewer

class ConsoleSqs:
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
        self.lista=service.get_sqs_list()
        #self.lista_db = sorted(self.lista_db, key=lambda tup: tup["DBInstanceIdentifier"])
        self.dettaglio=service.get_queue
        self.send_queue_message=service.send_queue_message
        self.receive_queue_messages=service.receive_queue_messages
        self.delete_queue_message=service.delete_queue_message
        self.crea_window()

    def crea_window(self):
       #grid # https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        #grid see https://tkdocs.com/tutorial/grid.html
        self.frame.columnconfigure(2)
        self.frame1 = ttk.Frame(self.frame, width=350, height=630)
        self.frame1.grid(row = 1, column = 2, sticky = tk.W, padx = 2) 
        self.frame1.pack(side=LEFT, expand = 1)
        self.frame2 = ttk.Frame(self.frame, width=550, height=630)
        self.frame2.grid(row = 1, column = 2, sticky = tk.E, padx = 2) 
        self.frame2.pack(side=LEFT, expand = 1)
        #self.frame3 = ttk.Frame(self.frame, width=350, height=630)
        #self.frame3.grid(row = 1, column = 2, sticky = tk.E, padx = 2) 
        #self.frame3.pack(side=LEFT, expand = 1)
        self.scroll = Scrollbar(self.frame1)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=50)
        self.tree['columns'] = ('TopicArn', 'Nome')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("TopicArn", width=50)
        self.tree.column("Nome",width=380)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("TopicArn",text="TopicArn",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        i=1
        for sm in self.lista:
            name=sm.split("/")[-1]
            self.tree.insert(parent='',index='end',iid=i,text='',values=(sm,name ) )
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        self.SQS_selezionata = self.tree.item(item)['values'][0]
        self.SQS_selezionata_url=""
        for sqs in self.lista:
            if sqs==self.SQS_selezionata:
                self.SQS_selezionata_url=sqs
        if self.SQS_selezionata_url=="":
            print("ERRORE")
            return
        self.dettaglio_valore=self.dettaglio(self.SQS_selezionata_url)

        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="Queue: " + self.SQS_selezionata ).pack()
        #Label(self.frame2, text="Stato: " + istanza['State']['Name'] ).pack()
        #if istanza['State']['Name']=='running':
        #    Button(self.frame2, text = "Stop", command=self.send_stop).pack()
        #else:
        #    Button(self.frame2, text = "Start", command=self.send_start).pack()
        self.frame2a = ttk.Frame(self.frame2,height=500)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=20)
        self.tree2['columns'] = ('Chiave', 'Valore')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Chiave", width=300)
        self.tree2.column("Valore",anchor=CENTER,width=480)
        self.tree2.heading("#0",text="",anchor=CENTER)
        self.tree2.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree2.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        
        for key in self.dettaglio_valore:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,self.dettaglio_valore[key]) )
            i=i+1
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2)
        #Button(self.frame2b, text = "Definizione", command=self.show_definition).pack()
        Label(self.frame2b, text="Operazioni possibili" ).grid(row = 0, column = 0, sticky = W, pady = 2) #.pack()
        Button(self.frame2b, text = "Consuma coda", command=self.consuma).grid(row = 1, column = 0, sticky = W, pady = 2)# .pack()
        Button(self.frame2b, text = "Produci"     , command=self.produci).grid(row = 1, column = 1, sticky = W, pady = 2)# .pack()
        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)

    def consuma(self):
        lista=self.receive_queue_messages(self.SQS_selezionata_url)
        for msg in lista:
            if 'Body' in msg:
                msg_body = msg['Body']
            else:
                msg_body = str(msg)
            receipt_handle = msg['ReceiptHandle']
            self.delete_queue_message(self.SQS_selezionata_url, receipt_handle)
            JSONViewer(Toplevel(self.frame),msg_body,self.SQS_selezionata_url.split("/")[-1])
            self.open_detail(self.frame)
            return
        #JSONViewer(Toplevel(self.frame),"NESSUN MESSAGGIO",self.SQS_selezionata_url.split("/")[-1])
        tk.messagebox.showinfo(title= self.SQS_selezionata_url.split("/")[-1] , message="Nessun messaggio")#https://docs.python.org/3/library/tkinter.messagebox.html
        

    def produci(self): #https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        w_tag_child=Toplevel(self.frame2) # Child window 
        w_tag_child.geometry("600x300")#+ str(x) + "+" + str(y))  # Size of the window 
        w_tag_child.title(self.SQS_selezionata_url.split("/")[-1])
        l2 = Label(w_tag_child, text = "Content:")
        l2.grid(row = 1, column = 0, sticky = W, pady = 2)
        self.e2 = Entry(w_tag_child,textvariable="{}") #, width= 42)
        self.e2.grid(row = 1, column = 1, padx=20, pady=2, ipadx=150 , ipady=20)
        b1 = Button(w_tag_child, text = "Save", command=self.send_prod)
        b1.grid(row = 2, column = 1, sticky = E)
        self.e2.insert(0,"")#item = self.tree.selection()[0]
    
    def send_prod(self): #send_queue_message(profile_name,queue_url,msg_attributes,msg_body)
        formatted_json = json.dumps({'messageEvent':self.e2.get()})
        self.send_queue_message( self.SQS_selezionata_url, {}, formatted_json )
        for widget in self.frame2.winfo_children():
            widget.destroy()
        self.open_detail(self.frame)

if __name__ == '__main__':
    print("Error")