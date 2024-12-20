import tkinter as tk
from tkinter import ttk, messagebox
import boto3
import os
from tkinter import filedialog
import json
from botocore.exceptions import ClientError

class S3Commander:
    def __init__(self, root):
        self.root = root
        self.root.title("S3 Commander")
        self.root.geometry("1200x600")
        
        # Configurazione AWS
        self.current_profile = None
        self.s3_client = None
        self.current_bucket = None
        self.current_prefix = ""
        self.path_history = []
        
        self.load_aws_profiles()
        self.create_menu()
        self.setup_gui()
        
    def load_aws_profiles(self):
        """Carica i profili AWS dal file delle credenziali"""
        try:
            self.profiles = boto3.Session().available_profiles
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare i profili AWS: {str(e)}")
            self.profiles = []

    def create_menu(self):
        """Crea la barra dei menu dell'applicazione"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # Menu File
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Upload File", command=self.upload_file)
        file_menu.add_command(label="Download", command=self.download_file)
        file_menu.add_separator()
        file_menu.add_command(label="Nuova Cartella", command=self.create_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Elimina", command=self.delete_file)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.root.quit)

        # Menu Navigazione
        nav_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Navigazione", menu=nav_menu)
        nav_menu.add_command(label="Root", command=self.goto_root)
        nav_menu.add_command(label="Su", command=self.go_up)
        nav_menu.add_command(label="Aggiorna", command=self.refresh_files)
        
        # Menu Profili AWS
        self.profile_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Profili AWS", menu=self.profile_menu)
        for profile in self.profiles:
            self.profile_menu.add_radiobutton(
                label=profile,
                command=lambda p=profile: self.change_profile(p),
                variable=tk.StringVar(value=profile)
            )
            
        # Menu Bucket (verrà popolato dopo la selezione del profilo)
        self.bucket_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Bucket", menu=self.bucket_menu)

    def change_profile(self, profile_name):
        """Gestisce il cambio di profilo AWS"""
        try:
            self.current_profile = profile_name
            session = boto3.Session(profile_name=self.current_profile)
            self.s3_client = session.client('s3')
            
            # Aggiorna il menu dei bucket
            self.update_bucket_menu()
            
            # Reset delle variabili correnti
            self.current_bucket = None
            self.current_prefix = ""
            self.path_var.set("/")
            self.path_history = []
            self.tree.delete(*self.tree.get_children())
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel cambio di profilo: {str(e)}")

    def update_bucket_menu(self):
        """Aggiorna il menu dei bucket dopo il cambio di profilo"""
        # Pulisce il menu esistente
        self.bucket_menu.delete(0, tk.END)
        
        try:
            # Ottiene la lista dei bucket
            response = self.s3_client.list_buckets()
            for bucket in response['Buckets']:
                self.bucket_menu.add_radiobutton(
                    label=bucket['Name'],
                    command=lambda b=bucket['Name']: self.change_bucket(b),
                    variable=tk.StringVar(value=bucket['Name'])
                )
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei bucket: {str(e)}")

    def change_bucket(self, bucket_name):
        """Gestisce il cambio di bucket"""
        self.current_bucket = bucket_name
        self.current_prefix = ""
        self.path_var.set("/")
        self.path_history = []
        self.refresh_files()

    def setup_gui(self):
        # Frame principale
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame per il path e la ricerca
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        # Path corrente
        ttk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value="/")
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=40)
        self.path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Filtro di ricerca
        ttk.Label(path_frame, text="Filtro:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_files)
        search_entry = ttk.Entry(path_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Frame per la lista dei file
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview per i file
        columns = ('name', 'size', 'last_modified')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Configurazione colonne
        self.tree.heading('name', text='Nome')
        self.tree.heading('size', text='Dimensione')
        self.tree.heading('last_modified', text='Ultima modifica')
        
        self.tree.column('name', width=400)
        self.tree.column('size', width=100)
        self.tree.column('last_modified', width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack della Treeview e scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Binding per doppio click
        self.tree.bind('<Double-1>', self.on_double_click)

        # Lista per memorizzare tutti i file (per il filtro)
        self.all_files = []

    def goto_root(self):
        """Torna alla root del bucket"""
        self.current_prefix = ""
        self.path_var.set("/")
        self.path_history = []
        self.refresh_files()
    
    def go_up(self):
        """Risale di un livello nella gerarchia delle cartelle"""
        if self.current_prefix:
            # Rimuove l'ultimo livello dal prefix
            parts = self.current_prefix.rstrip('/').split('/')
            if len(parts) > 1:
                self.current_prefix = '/'.join(parts[:-1]) + '/'
            else:
                self.current_prefix = ""
            self.path_var.set('/' + self.current_prefix)
            self.refresh_files()
    
    def filter_files(self, *args):
        """Filtra i file in base al testo di ricerca"""
        search_text = self.search_var.get().lower()
        
        # Pulisce la vista corrente
        self.tree.delete(*self.tree.get_children())
        
        # Filtra e mostra i file che corrispondono al criterio di ricerca
        for item in self.all_files:
            if search_text in item['name'].lower():
                self.tree.insert('', 'end', values=(
                    item['name'],
                    item['size'],
                    item['last_modified']
                ))
    
    def refresh_files(self):
        """Aggiorna la lista dei file nel bucket/prefix corrente"""
        if not self.current_bucket:
            return
            
        try:
            # Pulisce la vista corrente
            self.tree.delete(*self.tree.get_children())
            self.all_files = []
            
            # Lista gli oggetti nel bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.current_bucket,
                Prefix=self.current_prefix,
                Delimiter='/'
            )
            
            # Aggiunge le cartelle
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    folder_name = prefix['Prefix'].split('/')[-2]
                    self.all_files.append({
                        'name': folder_name,
                        'size': '<DIR>',
                        'last_modified': ''
                    })
                    self.tree.insert('', 'end', values=(folder_name, '<DIR>', ''))
            
            # Aggiunge i file
            if 'Contents' in response:
                for item in response['Contents']:
                    if item['Key'] == self.current_prefix:
                        continue
                        
                    name = item['Key'].split('/')[-1]
                    size = f"{item['Size'] / 1024:.2f} KB"
                    last_modified = item['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.all_files.append({
                        'name': name,
                        'size': size,
                        'last_modified': last_modified
                    })
                    
                    self.tree.insert('', 'end', values=(name, size, last_modified))
                    
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento dei file: {str(e)}")
    
    def on_double_click(self, event):
        """Gestisce il doppio click su un elemento"""
        item = self.tree.selection()[0]
        name = self.tree.item(item)['values'][0]
        size = self.tree.item(item)['values'][1]
        
        if size == '<DIR>':
            self.path_history.append(self.current_prefix)
            self.current_prefix += name + "/"
            self.path_var.set('/' + self.current_prefix)
            self.refresh_files()
    
    def upload_file(self):
        """Gestisce l'upload di un file"""
        if not self.current_bucket:
            messagebox.showwarning("Attenzione", "Seleziona prima un bucket")
            return
            
        filename = filedialog.askopenfilename()
        if filename:
            try:
                key = self.current_prefix + os.path.basename(filename)
                self.s3_client.upload_file(filename, self.current_bucket, key)
                self.refresh_files()
                messagebox.showinfo("Successo", "File caricato con successo")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante l'upload: {str(e)}")
    
    def download_file(self):
        """Gestisce il download di un file"""
        if not self.tree.selection():
            messagebox.showwarning("Attenzione", "Seleziona un file da scaricare")
            return
            
        item = self.tree.selection()[0]
        name = self.tree.item(item)['values'][0]
        size = self.tree.item(item)['values'][1]
        
        if size == '<DIR>':
            messagebox.showwarning("Attenzione", "Non puoi scaricare una cartella")
            return
            
        save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=name)
        if save_path:
            try:
                key = self.current_prefix + name
                self.s3_client.download_file(self.current_bucket, key, save_path)
                messagebox.showinfo("Successo", "File scaricato con successo")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante il download: {str(e)}")
    
    def delete_file(self):
        """Elimina un file o una cartella"""
        if not self.tree.selection():
            messagebox.showwarning("Attenzione", "Seleziona un elemento da eliminare")
            return
            
        item = self.tree.selection()[0]
        name = self.tree.item(item)['values'][0]
        size = self.tree.item(item)['values'][1]
        
        if not messagebox.askyesno("Conferma", f"Sei sicuro di voler eliminare {name}?"):
            return
            
        try:
            key = self.current_prefix + name
            if size == '<DIR>':
                key = key + '/' if not key.endswith('/') else key
                paginator = self.s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=self.current_bucket, Prefix=key):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            self.s3_client.delete_object(Bucket=self.current_bucket, Key=obj['Key'])
            else:
                self.s3_client.delete_object(Bucket=self.current_bucket, Key=key)
                
            self.refresh_files()
            messagebox.showinfo("Successo", "Elemento eliminato con successo")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'eliminazione: {str(e)}")
    
    def create_folder(self):
        """Crea una nuova cartella"""
        if not self.current_bucket:
            messagebox.showwarning("Attenzione", "Seleziona prima un bucket")
            return
            
        folder_name = tk.simpledialog.askstring("Nuova Cartella", "Nome della cartella:")
        if folder_name:
            try:
                # In S3 le cartelle sono rappresentate da oggetti vuoti con uno slash finale
                key = self.current_prefix + folder_name + "/"
                self.s3_client.put_object(Bucket=self.current_bucket, Key=key)
                self.refresh_files()
                messagebox.showinfo("Successo", "Cartella creata con successo")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante la creazione della cartella: {str(e)}")

    def handle_keyboard_shortcuts(self, event):
        """Gestisce le scorciatoie da tastiera"""
        if event.state == 4:  # Ctrl
            if event.keysym == 'r':
                self.refresh_files()
            elif event.keysym == 'u':
                self.go_up()
            elif event.keysym == 'f':
                self.search_var.set('')  # Reset del filtro
                self.tree.focus_set()

if __name__ == '__main__':
    root = tk.Tk()
    app = S3Commander(root)
    
    # Binding scorciatoie da tastiera
    root.bind_all('<Control-r>', app.handle_keyboard_shortcuts)  # Ctrl+R per refresh
    root.bind_all('<Control-u>', app.handle_keyboard_shortcuts)  # Ctrl+U per salire
    root.bind_all('<Control-f>', app.handle_keyboard_shortcuts)  # Ctrl+F per focus sul filtro
    
    root.mainloop()