import boto3
from botocore.exceptions import ClientError
import logging
import json
import time
from datetime import datetime, timedelta #https://stackoverflow.com/questions/68448034/aws-boto3-datapoint-within-client-get-metric-statistics-displays-on-one-file-b

class AwsEventBridge:
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.lambda_client = boto3.client('lambda')
        self.logger = logging.getLogger(__name__)
        boto3.setup_default_session(profile_name=self.profile_name)

    def list(self,prefix):
        client = boto3.client('events')
        if len(prefix)>0:
            response = client.list_rules(
                NamePrefix=prefix,
                EventBusName='default',
                #NextToken='string',
                Limit=100
            )
        else:
            response = client.list_rules(EventBusName='default',Limit=100)
        if "Rules" in response:
            return response['Rules']
        return []

    def disable_role(self,name):
        client = boto3.client('events')
        response = client.disable_rule(
            Name=name,
            EventBusName='default'
        )
        return response
    def enable_role(self,name):
        client = boto3.client('events')
        response = client.enable_rule(
            Name=name,
            EventBusName='default'
        )
        return response

    def describe_rule(self,name):
        client = boto3.client('events')
        response = client.describe_rule(
            Name=name,
            EventBusName='default'
        )
        return response

def main():
    o=AwsEventBridge("default")
    print("EventBridge")
    lista= o.list("Alberto")
    for l in lista:
        print (l)
    print ("-------")
    o.disable_role(lista[0]["Name"])
    o.enable_role(lista[0]["Name"])
    o=o.describe_rule(lista[0]["Name"])
    print(o)

if __name__ == '__main__':
    main()
     
