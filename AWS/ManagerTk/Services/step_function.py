
from tkinter import *
import tkinter as tk
from  tkinter import ttk
import json
import sys
import os
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from Application.json_viewer import JSONViewer

class ConsoleStepFunction:
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
        self.lista=service.state_machine_list()
        self.dettaglio=service.state_machine_detail
        self.esecuzioni=service.state_machine_execution
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
        self.tree['columns'] = ('Nome', 'Tipo')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=350)
        self.tree.column("Tipo",width=80)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Tipo",text="Tipo",anchor=CENTER)
        i=1
        for sm in self.lista:
            self.tree.insert(parent='',index='end',iid=i,text='',
                values=(sm['name'],sm['type'] ) )
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        self.sm_selezionata = self.tree.item(item)['values'][0]
        self.sm_selezionata_arn=""
        for sm in self.lista:
            if sm['name']==self.sm_selezionata:
                self.sm_selezionata_arn=sm['stateMachineArn']
        if self.sm_selezionata_arn=="":
            print("ERRORE")
            return
        self.dettaglio_valore=self.dettaglio(self.sm_selezionata_arn)
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="StateMachine: " + self.sm_selezionata ).pack()
        #Label(self.frame2, text="Stato: " + istanza['State']['Name'] ).pack()
        #if istanza['State']['Name']=='running':
        #    Button(self.frame2, text = "Stop", command=self.send_stop).pack()
        #else:
        #    Button(self.frame2, text = "Start", command=self.send_start).pack()
        self.frame2a = ttk.Frame(self.frame2,height=500)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=10)
        self.tree2['columns'] = ('Chiave', 'Valore')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Chiave", width=200)
        self.tree2.column("Valore",anchor=CENTER,width=580)
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
        Button(self.frame2b, text = "Definizione", command=self.show_definition).pack()
        l_name= Label(self.frame2b, text="Esecuzioni" )
        l_name.pack()
        #l_name.bind("<Button-1>", lambda e:self.open_window_set_tag())
        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=15)
        self.tree3['columns'] = ('Nome', 'Esito' ,'Start','End')
        self.tree3.column("#0", width=0,  stretch=NO)
        self.tree3.column("Nome", width=350)
        self.tree3.column("Esito",anchor=CENTER,width=100)
        self.tree3.column("Start",anchor=CENTER,width=200)
        self.tree3.column("End",anchor=CENTER,width=200)
        self.tree3.heading("#0",text="",anchor=CENTER)
        self.tree3.heading("Nome",text="Nome",anchor=CENTER)
        self.tree3.heading("Esito",text="Esito",anchor=CENTER)
        self.tree3.heading("Start",text="Start",anchor=CENTER)
        self.tree3.heading("End",text="End",anchor=CENTER)
        i=0
        self.esecuzioni_list=self.esecuzioni(self.sm_selezionata_arn)
        for es in self.esecuzioni_list:
            self.tree3.insert(parent='',index='end',iid=i,text='',
                    values=(es['name'],es['status'],str(es['startDate']),str(es['stopDate'])) )
            #{'executionArn': 'arn:aws:states:eu-west-1:740456629644:execution:sfBonificiWaitingDaCedacri:testByBoto3',
            #  'stateMachineArn': 'arn:aws:states:eu-west-1:740456629644:stateMachine:sfBonificiWaitingDaCedacri', 
            # 'name': 'testByBoto3', 'status': 'FAILED', 
            # 'startDate': datetime.datetime(2023, 10, 17, 14, 57, 17, 318000, tzinfo=tzlocal()), 
            # 'stopDate': datetime.datetime(2023, 10, 17, 14, 57, 17, 704000, tzinfo=tzlocal())}
            i=i+1
        self.tree3.bind("<Double-1>", self.show_definition)
        self.tree3.pack()
        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)
    
    def show_definition(self): #(frame,profilo,lista_istanze,istanza):
        #self.open_window_set_tag()
        s=""
        for key in self.dettaglio_valore :
            if key=='definition':
                s = self.dettaglio_valore[key]
        JSONViewer(Toplevel(self.frame),s,self.sm_selezionata)

    def show_definition_old(self): #(frame,profilo,lista_istanze,istanza):
        s=""
        for key in self.dettaglio_valore :
            if key=='definition':
                s = self.dettaglio_valore[key]
        s=s.replace("\t","").replace("'","ß").replace("\\\"","'").replace("\"","'").replace("ß","\"")#.replace(" ","").replace("\\\"","\"")
        #ascii(s).replace("\\\n","\n")
        w_tag_child=Toplevel(self.frame2) # Child window 
        w_tag_child.geometry("500x400")#+ str(x) + "+" + str(y))  # Size of the window 
        w_tag_child.title("Definition of "+ self.sm_selezionata)
        text = tk.Text(w_tag_child)
        text.pack()
        s=json.dumps(s, sort_keys=True, allow_nan = True,indent=2)
        text.insert(tk.END, s[1:-1].replace("\\\n","\n") )
        text.config(state = tk.DISABLED)

if __name__ == '__main__':
    print("Error")