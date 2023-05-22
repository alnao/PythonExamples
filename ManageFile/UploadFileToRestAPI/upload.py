#Uploader Filer to Rest API
# in windows to generate exe
# > pip install PyInstaller 
# > pyInstaller  --onefile upload.py

import requests
import json
from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from datetime import datetime, timedelta, timezone
import jwt

C_jwt_signature='password'
C_api_endpoint="https://aaaaaaaaaaaaaa.execute-api.eu-west-1.amazonaws.com/dev"

def get_API_endpoint():
    url=C_api_endpoint
    return url

def create_token_jwt(utente):
    message = {'iss': utente,'exp': (datetime.now(timezone.utc) + timedelta(hours=1))}
    encoded_jwt = jwt.encode(message, C_jwt_signature , algorithm='HS256')
    return  encoded_jwt

def choose_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    return file_path

def create_header(encoded_jwt):
    headers={ "authorization": ""+ encoded_jwt
             ,"content-type": "application/x-www-form-urlencoded;charset=ISO-8859-15"
             ,"accept": "application/json"}
    return headers

def get_file(file_path, username):
    f = open(file_path, 'rb') #file={"file": (file_path, f) }
    file_name=file_path
    if "/" in file_name:
        file_name=file_name.split("/")[-1]
    if "\\" in file_name:
        file_name=file_name.split("\\")[-1]
    data = {"file": (file_name, f), "username":(None, user ) }
    return data

def get_username():
    user=''
    if os.getenv('username'):
        user=os.getenv('username')
    return user.lower()

def post_file(url, data, headers):
    print("CALL API with data")
    print(data)
    resp = requests.post(url,data=data,files=data, headers=headers )#, files=files
    print ( "status code " + str(resp.status_code) )
    print (resp.text)
    return resp

def check_response(resp,window_title):
    if resp.status_code == 201:
        print ("Success")
        data = json.loads(resp.text)
        print ( data)
        messagebox.showinfo(title=window_title, message="File caricato con successo",)
    else:
        print ("Failure")
        if "User: anonymous is not authorized to perform: execute-api" in resp.text :
            messagebox.showwarning(title=window_title, message="Impossibile collegarsi al server, verificare che la VPN sia attiva",)
        #elseif '{"message":"Unauthorized"}' in rest.txt:
        #    messagebox.showwarning(title=window_title, message="Impossibile caricare il file",)
        else:
            messagebox.showerror(title=window_title, message="Impossibile caricicare il file:" + resp.text,)

if __name__ == '__main__':
    url = get_API_endpoint()
    user = get_username()
    encoded_jwt = create_token_jwt(user)
    file_path = choose_file()
    data = get_file(file_path, user)
    headers = create_header(encoded_jwt)
    resp = post_file(url, data, headers)
    check_response(resp,"Uploader")