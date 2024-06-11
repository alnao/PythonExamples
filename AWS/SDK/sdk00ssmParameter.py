import json
import boto3
#see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm/client/get_parameters_by_path.html

class AwsSSMparameterStore:
    def __init__(self, profile_name):
        self.profile_name=profile_name
           
    def get_parameters_by_path(self,path):
        boto3.setup_default_session(profile_name=self.profile_name)
        ssm = boto3.client('ssm') #, 'us-east-2'
        paginator = ssm.get_paginator('get_parameters_by_path')
        response_iterator = paginator.paginate(
            Path=path,Recursive=True,WithDecryption=True#,MaxResults=123,
        )
        parameters=[]
        for page in response_iterator:
            for entry in page['Parameters']:
                parameters.append(entry)
        return parameters
        #ssm = boto3.client('ssm') #, 'us-east-2'
        #response = ssm.get_parameters_by_path(
        #    Path=path,Recursive=True,WithDecryption=True#,MaxResults=123,
        #)
        #if 'Parameters' in response:
        #    return response['Parameters']
        #return []
    def put_parameter(self, name, value, type, description):
        boto3.setup_default_session(profile_name=self.profile_name)
        ssm = boto3.client('ssm') #, 'us-east-2'
        response = ssm.put_parameter(
            Name=name,
            Description=description,
            Value=value,
            Type=type, #'String'|'StringList'|'SecureString',
            Overwrite=True, #|False,
            #AllowedPattern='string',
            Tier='Standard',#|'Advanced'|'Intelligent-Tiering',
            #Policies='string',
            #DataType='string'
        )
        return response

def main():
    print("Aws Py Console - SSM parameters")
    o=AwsSSMparameterStore("default")
    l=o.get_parameters_by_path("/nao")
    print (l)
    print (len(l))
    o.put_parameter("/nao/prova","prova1","String","Prova alberto 2")
    l=o.get_parameters_by_path("/nao")
    print (l)
    print("Aws Py Console - SSM parameters END")

if __name__ == '__main__':
    main()