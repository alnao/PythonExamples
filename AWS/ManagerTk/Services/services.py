from tkinter import *
import sys
import os
from Services.bucketS3 import ConsoleBucketS3
from Services.ec2 import ConsoleEc2
from Services.cloud_front import ConsoleCloudFront
from Services.ec2_security_groups import ConsoleEc2sg
from Services.ssm_parameter_store import ConsoleSSMparameterStore
from Services.lambda_function import ConsoleLambda
from Services.event_bridge import ConsoleEventBridge
from Services.step_function import ConsoleStepFunction
from Services.api_gateway import ConsoleApiGateway
from Services.dynamo import ConsoleDynamo
from Services.rds import ConsoleRds
from Services.glue_job import ConsoleGlueJob
from Services.sqs import ConsoleSqs
from Services.sns import ConsoleSns
from Services.elastic_ip import ConsoleElasticIp
from Services.efs import ConsoleEFS
from Services.auto_scaling import ConsoleAutoScaling
from Services.app_load_balancer import ConsoleAppLoadBalancer
from Services.cloud_watch_alarms import ConsoleCloudWatchAlarms
from Services.cloud_watch_logs import ConsoleCloudWatchLogs
from Services.ecr import ConsoleECR
#nota indispensabile che il pacakge SDK sia caricato dopo con l'istruzione qua sotto
#non sportare questa append sopra altrimenti andrebbe in un loop di import 
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) )
from SDK.profiles import AwsProfiles 
from SDK.ssm_parameter import AwsSSMparameterStore
from SDK.bucketS3 import AwsBucketS3 
from SDK.ec2 import AwsEc2,AwsEc2SecurityGroup 
from SDK.cloud_front import AwsCloudFront 
from SDK.lambda_function import AwsLambda
from SDK.event_bridge import AwsEventBridge
from SDK.step_function import AwsStepFunction
from SDK.api_gateway import AwsApiGateway
from SDK.dynamo import AwsDynamoDB
from SDK.rds import AwsRds
from SDK.glue_job import AwsGlueJob
from SDK.sqs import AwsSqs
from SDK.sns import AwsSns
from SDK.elastic_ip import AwsElasticIp
from SDK.efs import AwsEfs
from SDK.auto_scaling import AwsAutoScaling
from SDK.app_load_balancer import AwsAppLoadBalancer
from SDK.cloud_watch_alarms import AwsCloudWatchAlarm
from SDK.cloud_watch_logs import AwsCloudWatchLogs
from SDK.ecr import AwsEcr
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
            ,{'title':'Event Bridge','desc':'Lista delle regole Bridge','automatic':False,'classe':ConsoleEventBridge,'sdk':AwsEventBridge}
            ,{'title':'Step function','desc':'Lista delle state machine','automatic':False,'classe':ConsoleStepFunction,'sdk':AwsStepFunction}
            ,{'title':'Api Gateway','desc':'Lista delle API','automatic':False,'classe':ConsoleApiGateway,'sdk':AwsApiGateway}
            ,{'title':'DynamoDB','desc':'Lista delle tabelle Dynamo','automatic':False,'classe':ConsoleDynamo,'sdk':AwsDynamoDB}
            ,{'title':'RDS','desc':'Lista dei database RDS','automatic':False,'classe':ConsoleRds,'sdk':AwsRds }
            ,{'title':'GlueJob','desc':'Lista dei job Glue','automatic':False,'classe':ConsoleGlueJob,'sdk':AwsGlueJob }
            ,{'title':'Sqs','desc':'Lista di code SQS','automatic':False,'classe':ConsoleSqs,'sdk':AwsSqs }
            ,{'title':'Sns','desc':'Lista di code SNS','automatic':False,'classe':ConsoleSns,'sdk':AwsSns }
            ,{'title':'ElasticIP','desc':'Lista di ElasticIp','automatic':False,'classe':ConsoleElasticIp,'sdk':AwsElasticIp }
            ,{'title':'EFS','desc':'Lista dischi EFS','automatic':False,'classe':ConsoleEFS,'sdk':AwsEfs }
            ,{'title':'ASG','desc':'Lista AutoScaling','automatic':False,'classe':ConsoleAutoScaling,'sdk':AwsAutoScaling }
            ,{'title':'ALB','desc':'Lista AppLoadBalancer','automatic':False,'classe':ConsoleAppLoadBalancer,'sdk':AwsAppLoadBalancer }
            ,{'title':'CWAlarms','desc':'Lista Cloud Watch Alarms','automatic':False,'classe':ConsoleCloudWatchAlarms,'sdk':AwsCloudWatchAlarm }
            ,{'title':'CWLogs','desc':'Lista Cloud Watch Logs','automatic':False,'classe':ConsoleCloudWatchLogs,'sdk':AwsCloudWatchLogs }
            ,{'title':'ECR','desc':'Lista ECR','automatic':False,'classe':ConsoleECR,'sdk':AwsEcr }
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
