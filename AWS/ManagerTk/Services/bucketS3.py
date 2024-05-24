from urllib import request
from tkinter import *
import tkinter as tk
from  tkinter import ttk
from tkinter.filedialog import asksaveasfile #https://www.geeksforgeeks.org/python-asksaveasfile-function-in-tkinter/
from tkinter.filedialog import askopenfilename
from functools import partial

if __name__ == '__main__':
    print("Error")

class ConsoleBucketS3:
    larghezza_blocco=450
    altezza=600
    mol1=12/7 #larghezza colonne 
    mol2=12/3
    mol3=12/2

    def __init__(self,frame,profilo,configuration,lista_bucket,get_objects_method,get_txt_object,get_presigned_object,upload_file,list_to_clipboard 
                 ,bucketDefault,pathDefault,reload_method):
        for widget in frame.winfo_children():
            widget.destroy()
        self.configuration=configuration
        self.lista_bucket=lista_bucket
        self.profilo=profilo
        self.frame=frame
        self.get_objects_method=get_objects_method
        self.get_txt_object=get_txt_object
        self.get_presigned_object=get_presigned_object
        self.upload_file=upload_file
        self.reload_method=reload_method
        self.bucketDefault=bucketDefault
        self.pathDefault=pathDefault
        self.crea_window(bucketDefault,pathDefault)
        self.lista_o1=[]
        self.list_to_clipboard=list_to_clipboard

    def crea_window(self,bucketDefault,pathDefault):
        #grid # https://www.geeksforgeeks.org/python-grid-method-in-tkinter/
        #grid see https://tkdocs.com/tutorial/grid.html
        self.frame.columnconfigure(3)
        self.frame1 = ttk.Frame(self.frame, width=self.larghezza_blocco+10, height=self.altezza)
        self.frame1.grid(row = 1, column = 1, sticky = tk.NW, padx = 2) 
        self.frame1.pack(side=LEFT, expand = 1)
        self.frame2 = ttk.Frame(self.frame, width=self.larghezza_blocco+10, height=self.altezza)
        self.frame2.grid(row = 1, column = 2, sticky = tk.NW, padx = 2) 
        self.frame2.pack(side=LEFT, expand = 1)
        self.frame3 = ttk.Frame(self.frame, width=self.larghezza_blocco+10, height=self.altezza)
        self.frame3.grid(row = 1, column = 3, sticky = tk.NW, padx = 2) 
        self.frame3.pack(side=LEFT, expand = 1)
        self.scroll = Scrollbar(self.frame1)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=30)
        self.tree['columns'] = ('Nome')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Nome", width=self.larghezza_blocco)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Nome",text="Nome",anchor=CENTER)
        i=1
        for b in self.lista_bucket:
            self.tree.insert(parent='',index='end',iid=i,text='',values=(b["Name"]))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail_bucket)
        self.tree.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        self.tree.pack()
        self.free2_loaded=False
        self.free3_loaded=False
        #seleziono se arriva un Default
        if self.bucketDefault != "" :
            i=1
            for b in self.lista_bucket:
                if self.bucketDefault==b["Name"]:
                    child_id=self.tree.get_children()[i-1]
                    self.tree.focus(child_id)
                    self.tree.selection_set(child_id)
                    self.bucket_name = self.bucketDefault
                    self.open_detail_bucket_with_name("",self.bucketDefault)
                i=i+1
        #gestione S3 indicati nel file di configurazione , aggiungo bottoni e metodo e per aprirli
        if self.profilo in self.configuration:
            if 's3' in self.configuration[self.profilo]:
                self.frame1b = ttk.Frame(self.frame1, width=self.larghezza_blocco+10, height=30)
                self.frame1b.columnconfigure( len(self.configuration[self.profilo]['s3']) )
                #self.frame1b.grid(row = 1, column = len(self.configuration[self.profilo]['s3']), sticky = tk.NW, padx = 2) 
                for e in self.configuration[self.profilo]['s3']:
                    Button(self.frame1b, text = e['label'], #command=lambda: self.open_bucket_from_config_file( e )
                        command=partial(self.open_bucket_from_config_file , e )
                    ).pack(side=tk.LEFT)
                self.frame1b.pack(side=LEFT, expand = 1)
                
        #return tab

    #metodo per selezionare un bucket e un path a paritre da un bottone
    def open_bucket_from_config_file(self,row):
        self.bucket_name = row['bucket']
        self.open_detail_bucket_with_name(False,self.bucket_name)
        self.path_opened = row['path']+"/"
        i=1
        for b in self.lista_bucket:
            if b["Name"] == self.bucket_name :
                child_id=self.tree.get_children()[i-1]
                self.tree.focus(child_id)
                self.tree.selection_set(child_id)
            i=i+1
        if len(self.path_opened)>1:
            self.open_detail_folder(self.path_opened,"")
            i=1
            for f in self.folders:
                if f == self.path_opened :
                    child_id=self.tree2.get_children()[i-1]
                    self.tree2.focus(child_id)
                    self.tree2.selection_set(child_id)
                i=i+1
        


    def open_detail_bucket(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        self.bucket_name = self.tree.item(item)['values'][0]
        self.open_detail_bucket_with_name(event,self.bucket_name)

    def open_detail_bucket_with_name(self, event,bucket_name): #(frame,profilo,lista_istanze,istanza):
        #print ("Apro "+ self.bucket_name)
        self.lista_o1=self.get_objects_method(self.bucket_name,"")
        self.folders=[]
        files=[]
        if "folders" in self.lista_o1:
            for o in self.lista_o1["folders"]:
                self.folders.append(o["Prefix"]) #folder
        if "objects" in self.lista_o1:
            for o in self.lista_o1["objects"]:
                files.append(o) #file Key LastModified, ETag , Size, StorageClass

        if self.free2_loaded==True:
            for widget in self.frame2.winfo_children():
                widget.destroy()
            for widget in self.frame3.winfo_children():
                widget.destroy()
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            #print ("refresh frame2")
            self.frame2 = ttk.Frame(self.frame, width=self.larghezza_blocco-10, height=self.altezza-10)
            self.frame2.grid(row = 1, column = 2, sticky = tk.NW, padx = 2) 
            self.frame3.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame3 = ttk.Frame(self.frame, width=self.larghezza_blocco-10, height=self.altezza-10)
            self.frame3.grid(row = 1, column = 3, sticky = tk.NW, padx = 2) 
        lb=Label(self.frame2, text="Bucket: " + self.bucket_name + " (click to copy)" )
        lb.bind("<Button-1>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        lb.pack()
        self.frame2a = ttk.Frame(self.frame2,height=100)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=12)
        self.tree2['columns'] = ('Cartella')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Cartella", width=self.larghezza_blocco-10)
        self.tree2.heading("#0",text="",anchor=CENTER)
        self.tree2.heading("Cartella",text="Cartella",anchor=CENTER)
        i=0
        for f in self.folders:
            self.tree2.insert(parent='',index='end',iid=i,text='',values=(f) )
            i=i+1
        self.tree2.bind("<Double-1>", self.open_detail_folder_from_level1)
        self.tree2.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree2,0) )
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2)
        l_name= Label(self.frame2b, text="Files (double-click to upload)"  )
        l_name.bind("<Double-1>", self.upload_file_level1 )
        l_name.pack()
        #l_name.bind("<Button-1>", lambda e:self.open_window_set_tag())
        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree2b = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=16)
        self.tree2b['columns'] = ('Nome', 'Time','Size')
        self.tree2b.column("#0", width=0,  stretch=NO)
        self.tree2b.column("Nome", width=               int(self.larghezza_blocco/self.mol1))
        self.tree2b.column("Time",anchor=CENTER,width=  int(self.larghezza_blocco/self.mol2))
        self.tree2b.column("Size",anchor=CENTER,width=  int(self.larghezza_blocco/self.mol3)  )
        self.tree2b.heading("#0",text="",anchor=CENTER)
        self.tree2b.heading("Nome",text="Nome",anchor=CENTER)
        self.tree2b.heading("Time",text="Time",anchor=CENTER)
        self.tree2b.heading("Size",text="Size",anchor=CENTER)
        i=0
        for f in files:
            self.tree2b.insert(parent='',index='end',iid=i,text='',
                    values=(f['Key'],str(f['LastModified']),f['Size']) )
            i=i+1
        self.tree2b.bind("<Double-1>", self.download_file_level1)
        self.tree2b.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree2b,0) )
        self.tree2b.pack()
        self.frame2a.pack(side=TOP)
        self.frame2b.pack(side=BOTTOM)
        self.frame2.pack(side=LEFT, expand = 1)
        self.frame3.pack(side=LEFT, expand = 1)
        #print("pathDefault" + self.pathDefault )
        if self.pathDefault != "":
            i=1
            #print( folders )
            for f in self.folders:
                if f == self.pathDefault +"/" :
                    child_id=self.tree2.get_children()[i-1]
                    self.tree2.focus(child_id)
                    self.tree2.selection_set(child_id)
                    self.open_detail_folder(f,"")
                i=i+1

    def download_file_level1(self,event):
        item = self.tree2b.selection()[0]
        object=self.lista_o1["objects"][int(item)]
        self.download_file(object)

    def open_detail_folder_from_level1(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree2.selection()[0]
        if not "folders" in self.lista_o1:
            print("ERRORE folders vuoto ricarico")
            self.lista_o1=self.get_objects_method(self.bucket_name,"")
        folder=self.lista_o1["folders"][int(item)]
        self.path_opened = folder["Prefix"]
        self.open_detail_folder(self.path_opened,"")

    def open_detail_folder(self, path, path_precedente):
        #print ("open_detail_folder " + path)
        self.lista_l1=self.get_objects_method(self.bucket_name,path)
        folders=[]
        files=[]
        if "folders" in self.lista_l1:
            for o in self.lista_l1["folders"]:
                folders.append(o["Prefix"]) #folder
        if "objects" in self.lista_l1:
            for o in self.lista_l1["objects"]:
                files.append(o) #file Key LastModified, ETag , Size, StorageClass
        if self.free3_loaded==True:
            self.frame3.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame3 = ttk.Frame(self.frame, width=self.larghezza_blocco, height=self.altezza-10)
        l=Label(self.frame3, text="Path: " + path + " (click to .. )")# (click to ../)
        l.bind("<Double-1>", self.open_parent_folder_from_level2)
        l.pack()
        self.frame3a = ttk.Frame(self.frame3,height=100)
        self.scroll3 = Scrollbar(self.frame3a)
        self.scroll3.pack(side=RIGHT, fill=Y)
        self.free3_loaded=True
        self.tree3 = ttk.Treeview(self.frame3a,yscrollcommand=self.scroll3.set,height=12)
        self.tree3['columns'] = ('Cartella')
        self.tree3.column("#0", width=0,  stretch=NO)
        self.tree3.column("Cartella", width=self.larghezza_blocco)
        self.tree3.heading("#0",text="",anchor=CENTER)
        self.tree3.heading("Cartella",text="Cartella",anchor=CENTER)
        i=0
        for f in folders:
            self.tree3.insert(parent='',index='end',iid=i,text='',values=(f.replace(path,"")) )
            i=i+1
        self.tree3.bind("<Double-1>", self.open_detail_folder_from_level2)
        self.tree3.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3,0) )
        self.tree3.pack()
        self.frame3b = ttk.Frame(self.frame3)
        l_name= Label(self.frame3b,text="Files (double-click to upload)") # + path  )
        self.path_selezionato=path
        l_name.bind("<Double-1>", self.upload_file_level2 )
        l_name.pack()
        self.scroll3b = Scrollbar(self.frame3b)
        self.scroll3b.pack(side=RIGHT, fill=Y)

        self.tree3b = ttk.Treeview(self.frame3b,yscrollcommand=self.scroll3b.set,height=16)
        self.tree3b['columns'] = ('Nome', 'Time','Size')
        self.tree3b.column("#0", width=0,  stretch=NO)
        self.tree3b.column("Nome", width=               int(self.larghezza_blocco/self.mol1))
        self.tree3b.column("Time",anchor=CENTER,width=  int(self.larghezza_blocco/self.mol2))
        self.tree3b.column("Size",anchor=CENTER,width=  int(self.larghezza_blocco/self.mol3))
        self.tree3b.heading("#0",text="",anchor=CENTER)
        self.tree3b.heading("Nome",text="Nome",anchor=CENTER)
        self.tree3b.heading("Time",text="Time",anchor=CENTER)
        self.tree3b.heading("Size",text="Size",anchor=CENTER)
        i=0
        for f in files:
            self.tree3b.insert(parent='',index='end',iid=i,text='',
                    values=(f['Key'].replace(path,""),str(f['LastModified']),f['Size']) )
            i=i+1
        self.tree3b.bind("<Double-1>", self.download_file_level2 )
        self.tree3b.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3b,0) )
        self.tree3b.pack()
        self.frame3a.pack(side=TOP)
        self.frame3b.pack(side=BOTTOM)
        self.frame3.pack(side=LEFT)
    
    def open_detail_folder_from_level2(self, event): #(frame,profilo,lista_istanze,istanza):
        print("open_detail_folder_from_level2")
        item = self.tree3.selection()[0]
        folder=self.lista_l1["folders"][int(item)]
        path_old =self.path_opened
        self.path_opened = folder["Prefix"]
        self.open_detail_folder(self.path_opened,path_old)

    def open_parent_folder_from_level2(self, event): #(frame,prof
        path_old =self.path_opened
        print("open_parent_folder_from_level2 " + path_old)
        if path_old.count("/")>1:#
            path_new=path_old.replace( (path_old.split("/")[-2])+"/" ,"")
            self.path_opened = path_new
            self.open_detail_folder(path_new,path_old)
        else:
            print("nothing to do " + path_old)
    
    def upload_file_level1(self, event):
        self.path_selezionato="" #sbianco la variabile potrebbe avere valore
        self.upload_file_window(self)
        self.open_detail_bucket_with_name(event,self.bucket_name)
    def upload_file_level2(self, event):
        self.upload_file_window(self)
        self.open_detail_folder(self.path_selezionato,self.path_selezionato)
    def upload_file_window(self, event):
        file_source=askopenfilename()
        #print( file_source )
        bucket=self.bucket_name
        key=self.path_selezionato + "" + file_source.split("/")[-1] #no "/" 
        self.upload_file(bucket,key,file_source)

    def download_file_level2(self,event):
        item = self.tree3b.selection()[0]
        object=self.lista_l1["objects"][int(item)]
        self.download_file(object)
        
    def download_file(self,object): 
        #print( object )
        file_name=object["Key"].split("/")[-1]
        files = [('File', file_name)]
        file_dest = asksaveasfile(filetypes = files, defaultextension = files,initialfile =file_name)
        #print("To save file : " + file_dest)
        #only text files
        #righe=self.get_txt_object(self.bucket_name,object["Key"])
        #with open(file_dest.name, "w") as f: # https://www.codingem.com/learn-python-how-to-write-to-a-file/
        #    for riga in righe:
        #        f.write(riga)
        #        f.write("\n")
        #print (item)
        #download with presigned signature
        url=self.get_presigned_object(self.bucket_name,object["Key"])
        #with requests.get(url, stream=True) as r:
        #    with open(file_dest.name, 'wb') as f:
        #        shutil.copyfileobj(r.raw, f)
        return request.urlretrieve(url, file_dest.name)
    
