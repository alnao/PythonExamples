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
        self.setup_gui()
        
    def load_aws_profiles(self):
        """Carica i profili AWS dal file delle credenziali"""
        try:
            self.profiles = boto3.Session().available_profiles
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare i profili AWS: {str(e)}")
            self.profiles = []

    def setup_gui(self):
        # Frame principale
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame superiore per i controlli
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Frame per profilo e bucket
        profile_frame = ttk.Frame(controls_frame)
        profile_frame.pack(fill=tk.X, pady=5)
        
        # Selezione profilo AWS
        ttk.Label(profile_frame, text="Profilo AWS:").pack(side=tk.LEFT, padx=5)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var)
        self.profile_combo['values'] = self.profiles
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_change)
        
        # Selezione bucket (allargata)
        ttk.Label(profile_frame, text="Bucket:").pack(side=tk.LEFT, padx=5)
        self.bucket_var = tk.StringVar()
        self.bucket_combo = ttk.Combobox(profile_frame, textvariable=self.bucket_var, width=50)
        self.bucket_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.bucket_combo.bind('<<ComboboxSelected>>', self.on_bucket_change)
        
        # Frame per il path e la ricerca
        path_frame = ttk.Frame(controls_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        # Path corrente con bottoni di navigazione integrati
        ttk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=5)
        
        # Pulsanti di navigazione (inizialmente nascosti)
        self.root_button = ttk.Button(path_frame, text="Root", command=self.goto_root)
        self.up_button = ttk.Button(path_frame, text="↑ Su", command=self.go_up)
        
        # Path entry (ridotto per fare spazio ai bottoni)
        self.path_var = tk.StringVar(value="/")
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=40)
        self.path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Gestione visibilità bottoni in base al path
        self.path_var.trace('w', self.update_nav_buttons)
        
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
        
        # Frame inferiore per i pulsanti
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Pulsanti
        ttk.Button(button_frame, text="Upload File", command=self.upload_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Download", command=self.download_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Elimina", command=self.delete_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Nuova Cartella", command=self.create_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Aggiorna", command=self.refresh_files).pack(side=tk.LEFT, padx=5)

        # Lista per memorizzare tutti i file (per il filtro)
        self.all_files = []
        
        # Inizializza lo stato dei bottoni di navigazione
        self.update_nav_buttons()

    def update_nav_buttons(self, *args):
        """Aggiorna la visibilità dei bottoni di navigazione in base al path corrente"""
        current_path = self.path_var.get()
        
        if current_path != "/" and current_path:
            # Unpack e repack i bottoni solo se non sono già visibili
            if not self.root_button.winfo_ismapped():
                self.root_button.pack(side=tk.LEFT, padx=2)
            if not self.up_button.winfo_ismapped():
                self.up_button.pack(side=tk.LEFT, padx=2)
        else:
            # Nascondi i bottoni
            self.root_button.pack_forget()
            self.up_button.pack_forget()

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
    
    def on_profile_change(self, event=None):
        """Gestisce il cambio di profilo AWS"""
        try:
            self.current_profile = self.profile_var.get()
            session = boto3.Session(profile_name=self.current_profile)
            self.s3_client = session.client('s3')
            
            # Aggiorna la lista dei bucket
            response = self.s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            self.bucket_combo['values'] = buckets
            
            # Reset delle variabili correnti
            self.current_bucket = None
            self.current_prefix = ""
            self.path_var.set("/")
            self.path_history = []
            self.tree.delete(*self.tree.get_children())
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel cambio di profilo: {str(e)}")
    
    def on_bucket_change(self, event=None):
        """Gestisce il cambio di bucket"""
        self.current_bucket = self.bucket_var.get()
        self.current_prefix = ""
        self.path_var.set("/")
        self.path_history = []
        self.refresh_files()
    
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
                    folder_name = prefix['Prefix'].split('/')[-2]  # Prende l'ultimo elemento senza lo slash
                    self.all_files.append({
                        'name': folder_name,
                        'size': '<DIR>',
                        'last_modified': ''
                    })
                    self.tree.insert('', 'end', values=(folder_name, '<DIR>', ''))
            
            # Aggiunge i file
            if 'Contents' in response:
                for item in response['Contents']:
                    # Salta l'oggetto se è uguale al prefix corrente
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
            # È una cartella, aggiorna il prefix
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
                # Costruisce la key per S3
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
                # Elimina tutti gli oggetti nella cartella
                key = key + '/' if not key.endswith('/') else key
                paginator = self.s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=self.current_bucket, Prefix=key):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            self.s3_client.delete_object(Bucket=self.current_bucket, Key=obj['Key'])
            else:
                # Elimina il singolo file
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

    def update_path_display(self):
        """Aggiorna la visualizzazione del path corrente"""
        display_path = '/' + self.current_prefix if self.current_prefix else '/'
        self.path_var.set(display_path)

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