import requests
from requests.auth import HTTPBasicAuth
import json
from pathlib import Path
# import tkinter as tk
import os

#import jwt
from datetime import datetime, timedelta, timezone
#message = {'iss': 'CLIENT_ID','exp': (datetime.now(timezone.utc) + timedelta(hours=23))}
#print (message)
#encoded_jwt = jwt.encode(message, 'password', algorithm='HS256')
encoded_jwt = 'token'

import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
file_path = filedialog.askopenfilename()

file_ids = ''
headers={ "authorization": ""+ encoded_jwt,"content-type": "application/x-www-form-urlencoded;charset=ISO-8859-15","accept": "application/json"}

# Upload file
f = open(file_path, 'rb') #file={"file": (file_path, f) }
file_name=file_path
if "/" in file_name:
    file_name=file_name.split("/")[-1]
if "\\" in file_name:
    file_name=file_name.split("\\")[-1]
user=''
if os.getenv('username'):
    user=os.getenv('username')
data = {"file": (file_name, f), "username":(None, user ) }

url="https://k0o1cwwg5e.execute-api.eu-west-1.amazonaws.com/dev"
resp = requests.post(url,data=data,files=data, headers=headers )#, files=files
print (resp.text)
print ( "status code " + str(resp.status_code) )

if resp.status_code == 201:
    print ("Success")
    data = json.loads(resp.text)
    print ( data)
    tk.messagebox.showinfo(title="Cherry Integration Tools Uploader", message="File caricato con successo",)
else:
    print ("Failure")
    if "User: anonymous is not authorized to perform: execute-api" in resp.text :
        tk.messagebox.showwarning(title="Cherry Integration Tools Uploader", message="Impossibile collegarsi al server, verificare che la VPN sia attiva",)
    else:
        tk.messagebox.showerror(title="Cherry Integration Tools Uploader", message=resp.text,)
