import boto3
from botocore.exceptions import ClientError
import logging
import json
import time
from datetime import datetime, timedelta #https://stackoverflow.com/questions/68448034/aws-boto3-datapoint-within-client-get-metric-statistics-displays-on-one-file-b

#see https://docs.aws.amazon.com/code-library/latest/ug/python_3_lambda_code_examples.html
#see https://github.com/awsdocs/aws-doc-sdk-examples/tree/main/python/example_code/lambda#code-examples

#see log https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html

class AwsLambda:
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.lambda_client = boto3.client('lambda')
        self.logger = logging.getLogger(__name__)
        boto3.setup_default_session(profile_name=self.profile_name)

    def list_functions(self):
        list=[]
        try:
            func_paginator = self.lambda_client.get_paginator("list_functions")
            for func_page in func_paginator.paginate():
                for func in func_page["Functions"]:
                    #print(func["FunctionName"])
                    desc = func.get("Description")
                    #if desc:
                    #    print(f"\t{desc}")
                    #print(f"\t{func['Runtime']}: {func['Handler']}")
                    list.append ( {'Name':func["FunctionName"], 'Description': func.get("Description"), "RunTime":func['Runtime'], } )
        except ClientError as err:
            self.logger.error( "Couldn't list functions. Here's why: %s: %s",err.response["Error"]["Code"],err.response["Error"]["Message"] )
            raise
        return list
    def get_function(self,function_name):
        try:
            func_paginator = self.lambda_client.get_paginator("list_functions")
            for func_page in func_paginator.paginate():
                for func in func_page["Functions"]:
                    if func["FunctionName"]==function_name:
                        return func
        except ClientError as err:
            self.logger.error( "Couldn't list functions. Here's why: %s: %s",err.response["Error"]["Code"],err.response["Error"]["Message"] )
            raise
        return None
    def invoke_function(self, function_name, function_params, get_log=False):
        """
        Invokes a Lambda function.
        :param function_name: The name of the function to invoke.
        :param function_params: The parameters of the function as a dict. This dict is serialized to JSON before it is sent to Lambda.
        :param get_log: When true, the last 4 KB of the execution log are included in the response.
        :return: The response from the function invocation.
        """
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(function_params),
                LogType="Tail" if get_log else "None",
            )
            self.logger.info("Invoked function %s.", function_name)
        except ClientError:
            self.logger.exception("Couldn't invoke function %s.", function_name)
            raise
        return response
    def get_statistic(self, function_name):
        cloudwatch=AwsLambdaCloudWatch(self.profile_name)
        log=cloudwatch.get_statistic(function_name)
        return log     
    def get_logs_stream(self, function_name):
        logs=AwsLambdaLogs(self.profile_name)
        log=logs.get_logs_stream(function_name)
        return log     
    def get_logs(self, function_name ):
        logs=AwsLambdaLogs(self.profile_name)
        streams=self.get_logs_stream(function_name)
        log=logs.get_logs(function_name,streams)
        return log     
    

class AwsLambdaCloudWatch():
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.cloudwatch_client = boto3.client('cloudwatch')
        self.logger = logging.getLogger(__name__)
        boto3.setup_default_session(profile_name=self.profile_name)

    def get_statistic(self, function_name):
        """
        Waits for the query to complete and retrieves the results.

        :param query_id: The ID of the initiated query.
        :type query_id: str
        :return: A list containing the results of the query.
        :rtype: list
        """
        while True:
            time.sleep(1)
            results = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    },
                ],
                StartTime=datetime.utcnow() - timedelta(days=1), #seconds=60*60*24),
                EndTime=datetime.utcnow(),
                Period=60,
                Statistics=['SampleCount'], #'|'Average'|'Sum'|'Minimum'|'Maximum',
                Unit='Count' # 'Seconds'|'Microseconds'|'Milliseconds'|'Bytes'|'Kilobytes'|'Megabytes'|'Gigabytes'|'Terabytes'|'Bits'|'Kilobits'|'Megabits'|'Gigabits'|'Terabits'|'Percent'|'Count'|'Bytes/Second'|'Kilobytes/Second'|'Megabytes/Second'|'Gigabytes/Second'|'Terabytes/Second'|'Bits/Second'|'Kilobits/Second'|'Megabits/Second'|'Gigabits/Second'|'Terabits/Second'|'Count/Second'|'None'
            )                
            return results.get("Datapoints", [])

class AwsLambdaLogs(): #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.log_client = boto3.client('logs')
        self.logger = logging.getLogger(__name__)
        boto3.setup_default_session(profile_name=self.profile_name)
    def get_logs_stream(self,function_name):
        log_group="/aws/lambda/"+function_name
        response = self.log_client.describe_log_streams(
            logGroupName=log_group, #logGroupIdentifier='string',
            #logStreamNamePrefix="/",# 'string',# Cannot order by LastEventTime with a logStreamNamePrefix.
            orderBy='LastEventTime', #'LogStreamName'|'LastEventTime',
            descending=True, #|False,
            #nextToken='string',
            limit=50)
        if 'logStreams' in response:
            return response['logStreams']
        return []
    def get_logs(self, function_name,streams): #aws logs filter-log-events --log-group-name "/aws/lambda/esempio04-S3Notification-XuE5shURUFvH"
        log_group="/aws/lambda/"+function_name
        loglist=[]
        for stream in streams:
            events = dict()
            next_token = None
            params = dict(
                logGroupName=log_group,
                logStreamName="",
                startFromHead=False,
            )            
            while next_token != events.get('nextBackwardToken', ''):
                next_token = events.get('nextBackwardToken')
                if next_token:
                    params["nextToken"] = next_token
                params["logStreamName"]=stream['logStreamName']
                events = self.log_client.get_log_events(**params)
                for event in events.get('events'):
                    loglist.append(event) #yield event
        return loglist



def main(name):
    ob=AwsLambda("default")
    l=ob.list_functions()
    print(l)
    print("-------------- get_function")
    o=ob.get_function(name)
    print(o)
    #print("--------------")
    #function_params={ "Records": [{"s3":{ "bucket":{ "name" : "esempio04s3notifica" }, "object" : {"key": "prova.csv"} } }] }
    #o=ob.invoke_function(name,function_params, get_log=True)
    #print(o)
    print("-------------- get_statistic")
    stats=ob.get_statistic(name)
    print(stats)
    print("-------------- get_logs_stream")
    streams=ob.get_logs_stream(name)
    print(streams)
    print("-------------- get_logs")
    o=ob.get_logs(name)
    print(o)
    for s in o:
        print (s['timestamp'])
        #my_date=datetime.fromtimestamp( s['timestamp']/1000 )
        #print ( my_date.strftime("%Y-%m-%d %H:%M:%S") )


if __name__ == '__main__':
    main("esempio04-S3Notification-XuE5shURUFvH")
     

