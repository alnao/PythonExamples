from tkinter import *
import sys
import os
from Services.bucketS3 import ConsoleBucketS3
from Services.ec2 import ConsoleEc2
#nota indispensabile che il pacakge SDK sia caricato dopo con l'istruzione qua sotto
#non sportare questa append sopra altrimenti andrebbe in un loop di import 
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from SDK.sdk00profiles import AwsProfiles as AwsProfilesSdk
from SDK.sdk01bucketS3 import AwsBucketS3 as AwsBucketS3Sdk
from SDK.sdk02ec2 import AwsEc2 as AwsEc2Sdk


if __name__ == '__main__':
    print("ERROR")
    
class ServiceManager:
    def __init__(self,caller):
        self.caller=caller
        self.lista_profili_aws=[]
        self.lista_funzionalita=[ 
            {'title':'S3','desc':'Lista bucket S3','automatic':True,'metodo':self.load_s3},
            {'title':'EC2','desc':'Lista istanze Ec2','automatic':False,'metodo':self.load_ec2},
            {'title':'SG','desc':'Lista Security Groups','automatic':False,'metodo':self.load_sg}
        ]
    def get_lista_funzionalita(self):
        return self.lista_funzionalita
    
# Profili
    def get_lista_profili(self):
        self.aws_profiles=AwsProfilesSdk()
        self.lista_profili_aws=self.aws_profiles.get_lista_profili() 
        return self.lista_profili_aws
    def set_active_profile(self,profile):
        self.aws_profiles.set_active_profile(profile)
# Global frame managment
    def reload_frame(self,method,frame):
        for widget in frame.winfo_children():
            widget.destroy()
        method(frame)

#S3
    def load_s3(self,frame): #,bucket,path
        frame.pack_propagate(False)
        s3 = AwsBucketS3Sdk(self.caller.profilo)
        ConsoleBucketS3(frame,self.caller.profilo,self.caller.configuration
            ,s3.bucket_list() #(self.profilo)
            ,s3.object_list_paginator
            ,s3.content_object_text
            ,s3.content_object_presigned
            ,s3.write_file #write_test_file
            ,self.caller.list_to_clipboard , "",""
            ,lambda e: self.reload_frame(self.load_s3,frame)
            )

    def load_ec2(self,frame):   
        frame.pack_propagate(False)
        ec2 = AwsEc2Sdk(self.caller.profilo)
        ConsoleEc2(frame,self.caller.profilo
            ,ec2.get_lista_istanze() #(self.profilo)
            ,ec2.set_tag
            ,ec2.stop_instance
            ,ec2.start_instance
            ,self.caller.list_to_clipboard
            ,lambda e: self.reload_frame(self.load_ec2,frame) ) # ,self.reload_ec2_instance_window )
#    def reload_ec2_instance_window(self,frame):#print ("reload_ec2_instance_window")
#        for widget in frame.winfo_children():
#            widget.destroy()
#        self.load_ec2_instance_window(frame)

#EC2 SG

    def load_sg(self,frame):   
        print("Eseguito load_sg TODO")
        return
        frame.pack_propagate(False)
        ec2 = AwsEc2Sdk(self.caller.profilo)
        print("load_ec2sg")
#TODO
        ConsoleEc2(frame,self.caller.profilo
            ,ec2.get_lista_istanze() #(self.profilo)
            ,ec2.set_tag
            ,ec2.stop_instance
            ,ec2.start_instance
            ,lambda e: self.reload_frame(self.load_sg,frame) )
