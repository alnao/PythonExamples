from tkinter import *
import sys
import os
from Services.bucketS3 import ConsoleBucketS3
from Services.ec2 import ConsoleEc2
from Services.cloudFront import ConsoleCloudFront
from Services.ec2_security_groups import ConsoleEc2sg
from Services.ssm_parameter_store import ConsoleSSMparameterStore
from Services.lambdaFunction import ConsoleLambda
#nota indispensabile che il pacakge SDK sia caricato dopo con l'istruzione qua sotto
#non sportare questa append sopra altrimenti andrebbe in un loop di import 
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from SDK.sdk00profiles import AwsProfiles 
from SDK.sdk00ssmParameter import AwsSSMparameterStore
from SDK.sdk01bucketS3 import AwsBucketS3 
from SDK.sdk02ec2 import AwsEc2,AwsEc2SecurityGroup 
from SDK.sdk04cloudFront import AwsCloudFront 
from SDK.sdk05lambda import AwsLambda
#non mettere nessun import dopo perchè os.path sarebbe in errore


if __name__ == '__main__':
    print("ERROR")
    
class ServiceManager:
    def __init__(self,caller):
        self.caller=caller
        self.lista_profili_aws=[]
        self.lista_funzionalita=[ 
            {'title':'S3','desc':'Lista bucket S3','automatic':True,'classe':ConsoleBucketS3,'sdk':AwsBucketS3}# 'metodo':self.load_s3}
            ,{'title':'EC2','desc':'Lista istanze Ec2','automatic':False,'classe':ConsoleEc2,'sdk':AwsEc2} #'metodo':self.load_ec2}
            ,{'title':'SG','desc':'Lista Security Groups','automatic':False,'classe':ConsoleEc2sg,'sdk':AwsEc2SecurityGroup}
            ,{'title':'CloudFront','desc':'Lista Cloud Front','automatic':False,'classe':ConsoleCloudFront,'sdk':AwsCloudFront}# 'metodo':self.load_cloudFront}
            ,{'title':'SSM','desc':'Lista SSM parameter store','automatic':False,'classe':ConsoleSSMparameterStore,'sdk':AwsSSMparameterStore}
            ,{'title':'Lambda','desc':'Lista delle Lambda Function','automatic':False,'classe':ConsoleLambda,'sdk':AwsLambda}
        ]
    def get_lista_funzionalita(self):
        return self.lista_funzionalita
    
# Profili
    def get_lista_profili(self):
        self.aws_profiles=AwsProfiles()
        self.lista_profili_aws=self.aws_profiles.get_lista_profili() 
        return self.lista_profili_aws
    def set_active_profile(self,profile):
        self.aws_profiles.set_active_profile(profile)
# Global frame managment
    def reload_frame(self,method,frame):
        for widget in frame.winfo_children():
            widget.destroy()
        method(frame)
