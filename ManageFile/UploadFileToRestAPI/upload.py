#Uploader Filer to Rest API
import requests
#from requests.auth import HTTPBasicAuth
import json
from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
#from datetime import datetime, timedelta, timezone

def get_API_endpoint():
    url="https://aaaaaaaaaaaaaaaaaa.execute-api.eu-west-1.amazonaws.com/dev"
    return url

#JWT TOKEN
def create_token_jwt():
    #message = {'iss': 'CLIENT_ID','exp': (datetime.now(timezone.utc) + timedelta(hours=23))}
    #print (message)
    #encoded_jwt = jwt.encode(message, 'password', algorithm='HS256')
    encoded_jwt = 'token'
    return  encoded_jwt

def choose_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    return file_path

def create_header(encoded_jwt):
    file_ids = ''
    headers={ "authorization": ""+ encoded_jwt
             ,"content-type": "application/x-www-form-urlencoded;charset=ISO-8859-15"
             ,"accept": "application/json"}

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
    return user

def post_file(url, data, headers):
    print("CALL API" + url)
    resp = requests.post(url,data=data,files=data, headers=headers )#, files=files
    print (resp.text)
    print ( "status code " + str(resp.status_code) )
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
        else:
            messagebox.showerror(title=window_title, message=resp.text,)

if __name__ == '__main__':
    url = get_API_endpoint()
    encoded_jwt = create_token_jwt()
    user = get_username()
    file_path = choose_file()
    data = get_file(file_path, user)
    headers = create_header(encoded_jwt)
    resp = post_file(url, data, headers)
    check_response(resp,"Uploader")
