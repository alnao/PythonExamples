from tkinter import *
import tkinter as tk
from  tkinter import ttk
from tkinter import simpledialog

class ConsoleDynamo:

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
        self.lista_tabelle=service.table_list()# lista_tabelle
        self.lista_elementi=service.full_scan_table
        self.put_element=service.write_element_with_id
        self.delete_element=service.delete_element_by_id
        self.crea_window()

    def crea_window(self):
        #grid # https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        #grid see https://tkdocs.com/tutorial/grid.html
        self.frame.columnconfigure(2)
        self.frame1 = ttk.Frame(self.frame, width=320, height=630)
        self.frame1.grid(row = 1, column = 2, sticky = tk.W, padx = 2) 
        self.frame1.pack(side=LEFT, expand = 1)
        self.frame2 = ttk.Frame(self.frame, width=770, height=630)
        self.frame2.grid(row = 1, column = 2, sticky = tk.E, padx = 2) 
        self.frame2.pack(side=LEFT, expand = 1)
        self.scroll = Scrollbar(self.frame1)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=30)
        self.tree['columns'] = ('Nome')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=300)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        i=1
        for dis in self.lista_tabelle:
            self.tree.insert(parent='',index='end',iid=i,text='',values=(dis))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        tabella_sel = self.tree.item(item)['values'][0]
        self.tabella_sel=tabella_sel
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
            self.frame2a.pack_forget()
            self.frame2b.pack_forget()
        Label(self.frame2, text="Nome: " + tabella_sel ).pack()
        Button(self.frame2, text = "New", command=self.modifica_new).pack()
        
        self.lista_elementi_return = self.lista_elementi(self.tabella_sel)
        if len(self.lista_elementi_return)==0:
            Label(self.frame2, text="Tabella vuota" ).pack()
            self.frame2.pack(side=LEFT)
            return
        if len(self.lista_elementi_return)>1000:
            Label(self.frame2, text="troppe righe, impossibile procedere" ).pack()
            self.frame2.pack(side=LEFT)
            return
        Label(self.frame2, text="(doppio click sulla riga per vederla)" ).pack()
        self.frame2a = ttk.Frame(self.frame2,height=100)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=15)
        self.tree2['columns'] = ('id','C1','C2','C3','C4','C5','C6')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("id", width=150)
        self.tree2.column("C1", width=150)
        self.tree2.column("C2", width=150)
        self.tree2.column("C3", width=150)
        self.tree2.column("C4", width=150)
        self.tree2.column("C5", width=150)
        self.tree2.column("C6", width=150)
        self.tree2.heading("#0",text="",anchor=CENTER)
        i=1
        self.tree2.heading("id",text="id")
        for keys in self.lista_elementi_return[0]:
            if i<=6 and keys!="id":
                self.tree2.heading("C"+str(i),text=keys)
                i=i+1
        if i<=1:
            self.tree2.heading("C2",text="null")
        if i<=2:
            self.tree2.heading("C3",text="null")
        if i<=3:
            self.tree2.heading("C4",text="null")
        if i<=4:
            self.tree2.heading("C5",text="null")
        if i<=5:
            self.tree2.heading("C6",text="null")
        i=1
        for row in self.lista_elementi_return:
            v1=""
            v2=""
            v3=""
            v4=""
            v5=""
            v6=""
            c=1
            id=row['id']
            for key in row:
                if c==1:
                    v1=str(row[key])
                if c==2:
                    v2=str(row[key])
                if c==3:
                    v3=str(row[key])
                if c==4:
                    v4=str(row[key])
                if c==5:
                    v5=str(row[key])
                if c==6:
                    v6=str(row[key])
                if key !='id':
                    c=c+1
            self.tree2.insert(parent='',index='end',iid=i,text='',values=(id,v1,v2,v3,v4,v5,v6) )
            i=i+1
        self.tree2.bind("<Double-1>", self.open_details)
        self.tree2.pack(side=TOP)
        self.frame2a.pack(side=TOP)
        self.frame2b = ttk.Frame(self.frame2)
        self.frame2b.pack(side=TOP)
        self.frame2.pack(side=TOP)

    def open_details(self, event):
        self.frame2b.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
        self.frame2b = ttk.Frame(self.frame)
        item = self.tree2.selection()[0]
        id_sel = self.tree2.item(item)['values'][0]
        self.selezionato={}
        for row in self.lista_elementi_return:
            if str(row['id'])==str(id_sel):
                self.selezionato=row
        idt= Label(self.frame2b,text="ID " + str(id_sel)) # + path  )
        #idt.bind("<Double-1>", self.upload_file_level2 )
        idt.pack()
        Button(self.frame2b, text = "Modifica", command=self.modifica).pack()
        Label(self.frame2b, text="(doppio click per copiare un valore)" ).pack()

        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree2b = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=16)
        self.tree2b['columns'] = ('Chiave', 'Valore')
        self.tree2b.column("#0", width=0,  stretch=NO)
        self.tree2b.column("Chiave", width=   150)
        self.tree2b.column("Valore",width=600)
        self.tree2b.heading("#0",text="",anchor=CENTER)
        self.tree2b.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree2b.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        for e in self.selezionato:
            self.tree2b.insert(parent='',index='end',iid=i,text='',
                    values=(e,str(self.selezionato[e]) ) )
            i=i+1
        self.tree2b.bind("<Double-1>", self.copy_value)
        self.tree2b.pack(side=TOP)
        self.frame2b.pack(side=TOP)

    def modifica_new(self):
        self.selezionato={} #senza id:'' così viene creato dalla API
        self.open_window_modifica(self.selezionato) 
    def modifica(self):
        self.open_window_modifica(self.selezionato)
    def open_window_modifica(self, element):
        altezza=len(element)*50+100
        if (len(element) ==0 ):
            altezza=300
        w_tag_child=Toplevel(self.frame2) # Child window 
        w_tag_child.geometry("600x" + str(altezza) )#+ str(x) + "+" + str(y))  # Size of the window 
        w_tag_child.title("Set tag to " + element['id'] if 'id' in element else "new element" ) #min = a if a < b else b
        b2 = Button(w_tag_child, text = "Add key", command=self.window_modifica_add_key)
        b2.grid(row = 0, column = 0, sticky = E)
        b1 = Button(w_tag_child, text = "Save", command=self.window_modifica_save_item)
        b1.grid(row = 0, column = 1, sticky = E)
        self.w_tag_child_i=1
        self.window_modifica={}
        for e in element:
            if str(e) != 'id':
                l = Label(w_tag_child, text = str(e) + ":")
                l.grid(row = self.w_tag_child_i, column = 0, sticky = W, pady = 2)
                entry_text = tk.StringVar()
                entry_text.set( str( element[e] ) ) #e.insert( 0 , str( element[e] ) )
                en = Entry(w_tag_child,textvariable=entry_text )
                en.grid(row = self.w_tag_child_i, column = 1, pady = 2)
                self.window_modifica[str(e)]=en
            self.w_tag_child_i=self.w_tag_child_i+1
        self.w_tag_child=w_tag_child

    def window_modifica_add_key(self):
        key= simpledialog.askstring("Input", "Enter Key ")
        value=""
        l = Label(self.w_tag_child, text = str(key) + ":")
        l.grid(row = self.w_tag_child_i, column = 0, sticky = W, pady = 2)
        entry_text = tk.StringVar()
        entry_text.set( str( value ) ) #e.insert( 0 , str( element[e] ) )
        en = Entry(self.w_tag_child,textvariable=entry_text )
        en.grid(row = self.w_tag_child_i, column = 1, pady = 2)
        self.window_modifica[key]=en
        self.w_tag_child_i=self.w_tag_child_i+1

    def window_modifica_save_item(self):
        elemento=self.selezionato
        for key in self.window_modifica: #aggiorno valori inseriti ciclando su tutti le key dell'elemento
            elemento[key]=self.window_modifica[key].get()
        self.put_element ( self.tabella_sel, elemento)  #(profile_name, table,element):
        for widget in self.frame2.winfo_children():
            widget.destroy()
        self.open_detail( event=None )

    def copy_value(self, event):
        self.to_clipboard(self.tree2b,1)
        
if __name__ == '__main__':
    print("Error")