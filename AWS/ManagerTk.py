import tkinter as tk
import os
import yaml #pip install pyyaml
from tkinter import *
from tkinter import Label
from tkinter import Label
from tkinter import ttk

from SDK.sdk00profiles import AwsProfiles as AwsProfilesSdk
from SDK.sdk01bucketS3 import AwsBucketS3 as AwsBucketS3Sdk
from SDK.sdk02ec2 import AwsEc2 as AwsEc2Sdk

from ManagerTk.Services.bucketS3 import ConsoleBucketS3
from ManagerTk.Services.ec2 import ConsoleEc2
from ManagerTk.menu import ConsoleMenu

#see example tk https://realpython.com/python-gui-tkinter/
class StatusBar(tk.Frame):
    def __init__(self, master,profilo):
        tk.Frame.__init__(self, master)
        self.label = tk.Label(self)
        self.label.pack(side=tk.LEFT)
        self.pack(side=tk.BOTTOM, fill=tk.X)
        self.profilo=profilo
        self.label.config(text="Profilo " + self.profilo )
    def set(self, newText):
        self.label.config(text="Profilo " + self.profilo + " - " + newText)

class AwsPyConsole:
    larghezza=1500
    altezza=700
    def __init__(self,configuration):
        self.profilo='default'
        self.root = tk.Tk()
        self.configuration=configuration
        # Create window
        self.root.title('Aws Py Console')
        x=0 #ex 10 ex root.winfo_screenwidth() // 6
        y=0 #ex 10 ex int(root.winfo_screenheight() * 0.1)
        self.root.geometry (''+str(self.larghezza)+'x'+str(self.altezza+30)+'+' + str(x) + "+" + str(y) ) #WIDTHxHEIGHT+TOP+LEFT
        #get AWS profiles
        self.aws_profiles=AwsProfilesSdk()
        self.lista_profili_aws=self.aws_profiles.get_lista_profili()
        #crete menu
        ConsoleMenu(self.root,self.lista_profili_aws,self.load_profile)
        if len(self.lista_profili_aws)>0:
            self.load_profile( self.root, self.lista_profili_aws[0] )
        self.root.mainloop()

    def list_to_clipboard(self, list, index):
        item = str ( list.selection()[0] )
        text = list.item(item)['values'][index]
        self.root.clipboard_clear()
        self.root.clipboard_append(str(text))
        self.status.set( str(text) )

    def add_text_to_frame(self,frame,text):
        Label(frame, text=text).pack()
        frame.pack_propagate(False)


    def main_frame(self,root,profilo): #nota: funziona solo se c'è un iframe nella main
        self.profilo=profilo
        if self.profilo=="": #nessun profilo selezionato dal menu
            self.frame1=tk.Frame(root,width=self.larghezza-24,height=self.altezza-24,bg="#EEEEEE")
            self.frame1.grid(row=0,column=0)
            self.add_text_to_frame(self.frame1,"Selezionare un profilo") # Label(frame1, text="Selezionare un profilo").pack()
            #frame1.pack_propagate(False)
            return
        self.frame1=tk.Frame(root,width=self.larghezza-25,height=self.altezza-25,bg="#EEEEEE")
        self.status = StatusBar(self.frame1, self.profilo)
        self.frame1.grid(row=0,column=0)
        #tabs window
        self.tabs = ttk.Notebook(self.frame1, width=self.larghezza-30, height=self.altezza-30)
        self.tabs.pack(fill=BOTH, expand=TRUE)
        self.frameT_profile = ttk.Frame(self.tabs)
        self.frameT_s3  = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2c
        self.frameT_ec2 = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2)
        self.frameT_cloudWatch = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_cloudFront = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_stepFunctions = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_eventBridge  = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_ssmParameter  = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_apigateway  = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_dynamodb  = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_rds  = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
        self.frameT_gluejob = ttk.Frame(self.tabs)#.grid(row=1, columnspan=2) #frame2e
#TABS 
        for e in self.lista_funzionalita:
            e_frame= ttk.Frame(self.tabs)
            self.tabs.add(e_frame , text=e['title'] ) #self.tabs.add(self.frameT_elastic_ip, text="Elastic IP")
            self.add_text_to_frame(e_frame,e['desc']+ " " + self.profilo) #self.add_text_to_frame(self.frameT_elastic_ip,"Elastic IP "+self.profilo)
            e['metodo'](self,frame=e_frame) #self.load_elastic_ip_window(self.frameT_elastic_ip)
            self.tabs.pack(expand=1, fill="both")

#PROFILEs
    def load_profile(self,root,profilo):
        self.main_frame(root,profilo)
        self.root.title('Aws Py Console - profilo attivo: ' + profilo)
#S3
    def load_s3_instance_window(self,frame): #,bucket,path
        frame.pack_propagate(False)
        s3 = AwsBucketS3Sdk(self.profilo)
        ConsoleBucketS3(frame,self.profilo,self.configuration
            ,s3.bucket_list() #(self.profilo)
            ,s3.object_list_paginator
            ,s3.content_object_text
            ,s3.content_object_presigned
            ,s3.write_file #write_test_file
            ,self.reload_s3_instance_window , "","")
    def reload_s3_instance_window(self,frame):#print ("reload_s3_instance_window")
        for widget in frame.winfo_children():
            widget.destroy()
        self.load_s3_instance_window(frame)
#EC2
    def load_ec2_instance(self,frame):   
        frame.pack_propagate(False)
        Button(frame, text = "Load", command= lambda: self.reload_ec2_instance_window(frame)).pack()
    def load_ec2_instance_window(self,frame):   
        frame.pack_propagate(False)
        ec2 = AwsEc2Sdk(self.profilo)
        ConsoleEc2(frame,self.profilo
            ,ec2.get_lista_istanze() #(self.profilo)
            ,ec2.set_tag
            ,ec2.stop_instance
            ,ec2.start_instance
            ,self.reload_ec2_instance_window )
    def reload_ec2_instance_window(self,frame):#print ("reload_ec2_instance_window")
        for widget in frame.winfo_children():
            widget.destroy()
        self.load_ec2_instance_window(frame)
        
# lista_funzionalita
    lista_funzionalita=[ 
            {'title':'S3','desc':'Lista bucket S3','metodo':load_s3_instance_window},
            {'title':'EC2','desc':'Lista istanze Ec2','metodo':load_ec2_instance},
        ]


if __name__ == '__main__':
    configuration={}
    if os.path.exists("./config.yaml"):
        configuration=yaml.safe_load(open("./config.yaml"))
    if os.path.exists("C:\\temp\\configConsole.yaml"):
        configuration=yaml.safe_load(open("C:\\temp\\configConsole.yaml"))
    p=AwsPyConsole(configuration)

""" Esempio di file yaml di configurazione
default:
  s3:
  - label: alberto incoming
    bucket: alberto-input
    path: INCOMING
  - label: alberto outgoing
    bucket: alberto-input
    path: OUTGOING
  - label: sftp-simulator
    bucket: formazione-sftp-simulator
    path: ''
"""