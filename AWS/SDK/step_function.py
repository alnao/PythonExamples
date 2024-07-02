import boto3
from botocore.exceptions import ClientError
import logging
import json
import time
from datetime import datetime, timedelta #https://stackoverflow.com/questions/68448034/aws-boto3-datapoint-within-client-get-metric-statistics-displays-on-one-file-b

class AwsStepFunction:
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.lambda_client = boto3.client('lambda')
        self.logger = logging.getLogger(__name__)
        boto3.setup_default_session(profile_name=self.profile_name)

    def state_machine_list(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('stepfunctions')
        response = client.list_state_machines(maxResults=100)
        if 'stateMachines' in response:
            return response['stateMachines']
        return[]

    def state_machine_detail(self,smArn):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('stepfunctions')
        response = client.describe_state_machine(    stateMachineArn=smArn)
        return response

    def state_machine_execution(self,smArn):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('stepfunctions')
        response = client.list_executions(
            stateMachineArn=smArn,
            #statusFilter='RUNNING'|'SUCCEEDED'|'FAILED'|'TIMED_OUT'|'ABORTED',
            maxResults=100,
            #nextToken='string',
            #mapRunArn='string'
        )
        if 'executions' in response:
            return response['executions']
        return []

    def state_machine_execution_detail(self,esecutionArn):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('stepfunctions')
        response = client.describe_execution(executionArn=esecutionArn)
        return response
        #see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions/client/describe_execution.html

    def state_machine_start(self,stateMachineArn,name,input):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('stepfunctions')
        response = client.start_execution(        stateMachineArn=stateMachineArn,       name=name,        input=input   )
        return response
        #see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions/client/start_execution.html

def main(profile):
    print("Aws Py Console - Step functions START")
    print("-----------")
    o=AwsStepFunction(profile)
    lista_b=o.state_machine_list()
    for b in lista_b:
        print (b["name"] + "|" + b["type"] + "|" + b["stateMachineArn"] + "|" + str(b["creationDate"]) )
    print("-----------")
    if len(lista_b)==0:
        return
    r=o.state_machine_detail(lista_b[12]['stateMachineArn'])
    print ( r )
    print("-----------")
    r=o.state_machine_execution(lista_b[12]['stateMachineArn'])
    print ( r )
    print("-----------")
    if len(r)>0:
        r=o.state_machine_execution_detail(r[0]['executionArn'])
        print ( r )
        print("-----------")
    #r=o.state_machine_start(lista_b[12]['stateMachineArn'],"testByBoto3", "{ \"filename\": \"prova.csv\" , \"SkipDeleteSourceFile\" : false }" )
    #print ( r )
    #print("-----------")
    r=o.state_machine_execution(lista_b[12]['stateMachineArn'])
    print ( r )
    print("----------- END")

if __name__ == '__main__':
    main("default")
