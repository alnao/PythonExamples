from tkinter import *
import tkinter as tk
from  tkinter import ttk
import json
import sys
import os
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from Application.json_viewer import JSONViewer

class ConsoleEventBridge:
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
        self.list=service.list("")
        self.list = sorted(self.list, key=lambda tup: tup["Name"])
        self.describe_rule=service.describe_rule
        self.disable_role_m=service.disable_role
        self.enable_role_m=service.enable_role
        self.crea_window()

    def crea_window(self):
        #grid # https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        #grid see https://tkdocs.com/tutorial/grid.html
        self.frame.columnconfigure(2)
        self.frame1 = ttk.Frame(self.frame, width=550, height=630)
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
        self.tree['columns'] = ('Nome', 'Stato')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=450)
        self.tree.column("Stato",width=80)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Stato",text="Stato",anchor=CENTER)
        i=1
        for e in self.list:
            if 'Description' in e:
                self.tree.insert(parent='',index='end',iid=i,text='',
                    values=( e['Name'] , e['State']  ) )   
            else:
                self.tree.insert(parent='',index='end',iid=i,text='',
                    values=( e['Name'] , e['State']  ) )    
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        self.regola_selezionata = self.tree.item(item)['values'][0]
        self.dettaglio_valore=self.describe_rule(self.regola_selezionata)
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="Event Bridge: " + self.regola_selezionata ).pack()
        Label(self.frame2, text="Stato: " + self.dettaglio_valore['State'] ).pack()
        if self.dettaglio_valore['State']=='ENABLED':
            Button(self.frame2, text = "Disable", command=self.disable_role).pack()
        else:
            Button(self.frame2, text = "Enable", command=self.enable_role).pack()
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
        #l_name= Label(self.frame2b, text="Dettaglio" )
        #l_name.pack()
        #text = tk.Text(self.frame2b)
        #text.pack()
        s="NULL"
        if 'EventPattern' in self.dettaglio_valore:
            Button(self.frame2b, text = "Apri dettaglio json", command=self.show_definition).pack()
            s=self.dettaglio_valore['EventPattern']
            s=""+json.dumps(s, indent=2) #sort_keys=True, 
            s=s[1:-1].replace("\\\"","\"").replace("\n","")
        else:
            s=json.dumps(self.dettaglio_valore, sort_keys=True, indent=4)
        #text.insert(tk.END,s)
        #text.config(state = tk.DISABLED)
        Label(self.frame2b, text=s ).pack()
        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)

    def show_definition(self): #(frame,profilo,lista_istanze,istanza):
        #self.open_window_set_tag()
        s=""
        for key in self.dettaglio_valore :
            if key=='EventPattern':
                s = self.dettaglio_valore[key]
        JSONViewer(Toplevel(self.frame),s,self.regola_selezionata)
    
    def open_detail_tag(self, event): #(frame,profilo,lista_istanze,istanza):
        self.open_window_set_tag()
        item = self.tree3.selection()[0]
        print (item)
        key = self.tree3.item(item)['values'][0]
        value = self.tree3.item(item)['values'][1]
        self.e1.insert(0,key)
        self.e2.insert(0,value)#item = self.tree.selection()[0]

    def open_window_set_tag(self): #https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        w_tag_child=Toplevel(self.frame2) # Child window 
        #x=root.winfo_screenwidth() // 6
        #y=int(root.winfo_screenheight() * 0.1)
        w_tag_child.geometry("400x200")#+ str(x) + "+" + str(y))  # Size of the window 
        w_tag_child.title("Set tag to " + self.nome)
        #Label(w_tag_child, text="Set tag to " + self.nome ).pack()
        # this will create a label widget
        l1 = Label(w_tag_child, text = "Key:")
        l2 = Label(w_tag_child, text = "Value:")
        # grid method to arrange labels in respective
        # rows and columns as specified
        l1.grid(row = 0, column = 0, sticky = W, pady = 2)
        l2.grid(row = 1, column = 0, sticky = W, pady = 2)
        # entry widgets, used to take entry from user
        self.e1 = Entry(w_tag_child)
        self.e2 = Entry(w_tag_child)
        # this will arrange entry widgets
        self.e1.grid(row = 0, column = 1, pady = 2)
        self.e2.grid(row = 1, column = 1, pady = 2)
        b1 = Button(w_tag_child, text = "Save", command=self.send_set_tag)
        b1.grid(row = 2, column = 1, sticky = E)
        
    def disable_role(self):
        self.disable_role_m(self.regola_selezionata)
        self.reload_method()
    def enable_role(self):
        self.enable_role_m(self.regola_selezionata)
        self.reload_method()

if __name__ == '__main__':
    print("Error")