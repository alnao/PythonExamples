
from tkinter import *
import tkinter as tk
from  tkinter import ttk

#import window.ec2_instances as ec2_instances
#see https://www.pythontutorial.net/tkinter/tkinter-menu/
#see https://pythonguides.com/python-tkinter-table-tutorial/
# https://stackoverflow.com/questions/3794268/command-for-clicking-on-the-items-of-a-tkinter-treeview-widget

class ConsoleSSMparameterStore:
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
        self.lista_parametri=service.get_parameters_by_path("/")
        self.crea_parametro=service.put_parameter
        self.crea_window()

    def crea_window(self):
        self.frame.columnconfigure(3)
        self.frame1 = ttk.Frame(self.frame, width=550, height=600)
        self.frame1.grid(row = 1, column = 1, sticky = tk.W, padx = 2) 
        self.frame1.pack(side=LEFT, expand = 1)
        self.frame2 = ttk.Frame(self.frame, width=650, height=630)
        self.frame2.grid(row = 1, column = 2, sticky = tk.E, padx = 2) 
        self.frame2.pack(side=LEFT, expand = 1)
        Button(self.frame1, text = "Crea nuovo parametro", command=self.open_window_create).pack()
        self.scroll = Scrollbar(self.frame1)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=28)
        self.tree['columns'] = ('Nome', 'Type')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=340)
        self.tree.column("Type",width=80)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Type",text="Type",anchor=CENTER)
        i=1
        for param in self.lista_parametri:
            Name=param['Name']
            Type=param['Type']
            self.tree.insert(parent='',index='end',iid=i,text='', values=(Name,Type))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.free2_loaded=False
        self.tree.pack(side=LEFT, expand = 1)


    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        name_selected = self.tree.item(item)['values'][0]
        for parametri_ciclo in self.lista_parametri:
            if name_selected==parametri_ciclo['Name']:
                self.distribuzione=parametri_ciclo
                #print(parametri_ciclo)
                
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="Nome: " + self.distribuzione['Name'] ).pack()
        Label(self.frame2, text="Value: " + self.distribuzione['Value'] ).pack()
        if "String"==self.distribuzione['Type']:
            Button(self.frame2, text = "Modifica valore parametro", command=self.open_window_edit).pack()

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
        for key in self.distribuzione:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,self.distribuzione[key]) )
            i=i+1
        self.tree2.pack()
        
        self.frame2a.pack()
        self.frame2.pack(side=LEFT)

    def open_window_edit(self):
        self.open_window_create()
        self.e1.delete(0, END)
        self.e2.delete(0, END)
        self.e1.insert(0, self.distribuzione['Name']  )
        self.e2.insert(0, self.distribuzione['Value'] )

    def open_window_create(self): #https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        w_tag_child=Toplevel(self.frame2) # Child window 
        w_tag_child.geometry("400x200")#+ str(x) + "+" + str(y))  # Size of the window 
        w_tag_child.title("Set SSM parameter")
        l1 = Label(w_tag_child, text = "Name:")
        l2 = Label(w_tag_child, text = "Value:")
        l1.grid(row = 0, column = 0, sticky = W, pady = 2)
        l2.grid(row = 1, column = 0, sticky = W, pady = 2)
        self.e1 = Entry(w_tag_child, width= 42)
        self.e2 = Entry(w_tag_child, width= 42)
        self.e1.grid(row = 0, column = 1, pady = 2)
        self.e2.grid(row = 1, column = 1, pady = 2)
        b1 = Button(w_tag_child, text = "Save", command=self.send_creation)
        b1.grid(row = 2, column = 1, sticky = E)
        self.e1.insert(0,"/dev/example")
        self.e2.insert(0,"")#item = self.tree.selection()[0]

    def send_creation(self):        
        #put_parameter(profile_name, name, value, type, description)
        self.crea_parametro(self.e1.get(), self.e2.get() , "String" , self.e1.get() )
        self.reload_method() #self.frame)

if __name__ == '__main__':
    print("Error")