from tkinter import *
import tkinter as tk
from  tkinter import ttk
#import window.ec2_instances as ec2_instances

#see https://www.pythontutorial.net/tkinter/tkinter-menu/
#see https://pythonguides.com/python-tkinter-table-tutorial/
# https://stackoverflow.com/questions/3794268/command-for-clicking-on-the-items-of-a-tkinter-treeview-widget

class ConsoleEc2:
    def __init__(self,frame,profilo,lista_istanze,set_tag_method,stop_method,start_method,reload_method): #def crea_lista_istanze(frame,profilo,lista_istanze):#,load_profile_function
        self.lista_istanze=lista_istanze
        self.profilo=profilo
        self.frame=frame
        self.istanza={}
        self.nome=''
        self.set_tag_method=set_tag_method
        self.stop_method=stop_method
        self.start_method=start_method
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
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=50)
        self.tree['columns'] = ('Nome', 'Id', 'Tipo', 'Stato')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=240)
        self.tree.column("Id",anchor=CENTER,width=130)
        self.tree.column("Tipo",width=80)
        self.tree.column("Stato",width=80)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        self.tree.heading("Id",text="Id",anchor=CENTER)
        self.tree.heading("Tipo",text="Tipo",anchor=CENTER)
        self.tree.heading("Stato",text="Stato",anchor=CENTER)
        i=1
        for reservation in self.lista_istanze['Reservations']:
            for istanza in reservation['Instances']:
                nome=''
                if 'Tags' in istanza: #len(istanza.Tags)>0 :
                    for tag in istanza['Tags']:#print (tag)
                        if tag['Key']=='Name':
                            nome=tag['Value']
                self.tree.insert(parent='',index='end',iid=i,text='',
                    values=(nome,istanza['InstanceId'],istanza['InstanceType'], istanza['State']['Name']))
                i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        id_istanza = self.tree.item(item)['values'][1]
        istanza={}
        nome=''
        for reservation in self.lista_istanze['Reservations']:
            for istanza_ciclo in reservation['Instances']:
                if id_istanza==istanza_ciclo['InstanceId']:
                    istanza=istanza_ciclo
                    if 'Tags' in istanza: #len(istanza.Tags)>0 :
                        for tag in istanza['Tags']:
                            if tag['Key']=='Name':
                                nome=tag['Value']
        self.istanza=istanza
        self.nome=nome
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        Label(self.frame2, text="Istanza: " + id_istanza ).pack()
        Label(self.frame2, text="Stato: " + istanza['State']['Name'] ).pack()
        if istanza['State']['Name']=='running':
            Button(self.frame2, text = "Stop", command=self.send_stop).pack()
        else:
            Button(self.frame2, text = "Start", command=self.send_start).pack()
        Label(self.frame2, text="Nome: " + nome ).pack()
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
        for key in istanza:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,istanza[key]) )
            i=i+1
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2)
        l_name= Label(self.frame2b, text="Tag (click per inserire) " + nome )
        l_name.pack()
        l_name.bind("<Button-1>", lambda e:self.open_window_set_tag())
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
        for tag in istanza['Tags']:
            self.tree3.insert(parent='',index='end',iid=i,text='',
                    values=(tag['Key'],tag['Value']) )
            i=i+1
        self.tree3.bind("<Double-1>", self.open_detail_tag)
        self.tree3.pack()
        self.frame2a.pack()
        self.frame2b.pack()
        self.frame2.pack(side=LEFT)
    
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
        
    def send_set_tag(self):        #https://stackhowto.com/how-to-get-value-from-entry-on-button-click-in-tkinter/
        self.set_tag_method(self.istanza['InstanceId'], self.e1.get(), self.e2.get() )
        self.reload_method( self.frame )
    def send_stop(self):
        self.stop_method(self.istanza['InstanceId'])
        self.reload_method( self.frame )
    def send_start(self):
        self.start_method(self.istanza['InstanceId'])
        self.reload_method( self.frame )

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Aws Py Console - only ec2_instances')
    root.geometry ('950x680') #WIDTHxHEIGHT+TOP+LEFT
    frame2 = ttk.Frame(root)
    frame2.pack_propagate(False)
    Ec2InstanceWindow(frame2,"default",
        {'Reservations':[{'Instances':[{'InstanceId':'i1','InstanceType':'t2','State':{'Name':'main'} } ] }] } 
    ,print,print,print,print)
    frame2.pack()
    root.mainloop()