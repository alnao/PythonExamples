
import boto3
import logging
#import os
#import json
#import datetime
#import uuid
#from decimal import Decimal
#from boto3.dynamodb.conditions import Attr
#from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

class AwsGlueJob:
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.lambda_client = boto3.client('lambda')
        self.logger = logging.getLogger(__name__)
        boto3.setup_default_session(profile_name=self.profile_name)

        
    def jobs_list(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('glue')
        response = client.get_jobs(
            #NextToken='string',
            MaxResults=123
        )
        if "Jobs" in response:
            return response["Jobs"]
        return response
    #  {'Name': 'documentazione-epc-to-box', 'Description': '', 'Role': 'arn:aws:iam::xxxx:role/ExportDocumentiDaEPC-GlueExecutionRole-1NE952LG3LC5V', 
    # 'CreatedOn': datetime.datetime(2023, 9, 14, 9, 8, 0, 794000, tzinfo=tzlocal()), 'LastModifiedOn': datetime.datetime(2023, 10, 13, 17, 14, 53, 392000, tzinfo=tzlocal()), 
    # 'ExecutionProperty': {'MaxConcurrentRuns': 20}, 
    # 'Command': {'Name': 'glueetl', 'ScriptLocation': 's3://alberto-input/OUTGOING/exportBase/crea_zip_per_box.py', 'PythonVersion': '3'}, 
    # 'DefaultArguments': {'--EXPORT_FILE': 'listaFileDaEspotare.csv', '--enable-continuous-log-filter': 'true', '--enable-job-insights': 'true', 
        # '--BOX_CLIENTSECRET': '5yXfD69QVMWSCQh6d9Yhndpilo5JXXl6', '--additional-python-modules': 'boxsdk pyspark', '--enable-continuous-cloudwatch-log': 'true', 
        # '--BOX_CLIENTID': 'z8oxw6h8znl2z2h7d2upm8jipe6ueo7n', '--DEST_BUCKET': 'alberto-input', '--EXPORT_PATH': 'OUTGOING/exportBase', 
        # '--BOX_FOLDERID': '216961038333', '--job-language': 'python', '--TempDir': 's3://alberto-input/OUTGOING/exportBase/temp/'}, 
    # 'MaxRetries': 0, 'AllocatedCapacity': 2, 'Timeout': 2880, 'MaxCapacity': 2.0, 'WorkerType': 'G.1X', 'NumberOfWorkers': 2, 'GlueVersion': '3.0', 
    #'ExecutionClass': 'STANDARD'}

    def job_detail(self,job_name):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('glue')
        response = client.get_job(JobName=job_name)
        if "Job" in response:
            return response["Job"]
        return response

    def job_execution_list(self,job_name):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('glue')
        response = client.get_job_runs(
            JobName=job_name,
            #NextToken='string',
            MaxResults=123
        )
        if "JobRuns" in response:
            return response["JobRuns"]
        return []
    #{'Id': 'jr_35844f7126b8877fb6242d82dffd0032e0d01098529d08818601a69c40c4d7c1', 'Attempt': 0, 'JobName': 'documentazione-epc-to-box', 
    #'StartedOn': datetime.datetime(2023, 12, 13, 14, 58, 11, 582000, tzinfo=tzlocal()), 
    #'LastModifiedOn': datetime.datetime(2023, 12, 13, 14, 59, 35, 585000, tzinfo=tzlocal()), 
    #'CompletedOn': datetime.datetime(2023, 12, 13, 14, 59, 35, 585000, tzinfo=tzlocal()), 
    #'JobRunState': 'SUCCEEDED', 'Arguments': {'--cartella_run': '20231213_135353', '--gruppo_id': '1'}, 
    #'PredecessorRuns': [], 'AllocatedCapacity': 2, 'ExecutionTime': 72, 'Timeout': 2880, 'MaxCapacity': 2.0, 'WorkerType': 'G.1X', 
    # 'NumberOfWorkers': 2, 'LogGroupName': '/aws-glue/jobs', 'GlueVersion': '3.0', 'ExecutionClass': 'STANDARD'}

    def job_execution_detail(self,job_name,run_id):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('glue')
        response = client.get_job_run(
            JobName=job_name,
            RunId=run_id,
            PredecessorsIncluded=True #|False
        )
        return response

    def job_start(profile_name,job_name,run_id):
        print("TODO job_start " + job_name )
        #boto3.setup_default_session(profile_name=profile_name)
        #client = boto3.client('glue')
        #response = client.start_job_run(
        #    JobName='string',
        #    JobRunId='string',
        #    Arguments={
        #        'string': 'string'
        #    },
        #    AllocatedCapacity=123,
        #    Timeout=123,
        #    MaxCapacity=123.0,
        #    SecurityConfiguration='string',
        #    NotificationProperty={
        #        'NotifyDelayAfter': 123
        #    },
        #    WorkerType='Standard'|'G.1X'|'G.2X'|'G.025X'|'G.4X'|'G.8X'|'Z.2X',
        #    NumberOfWorkers=123,
        #    ExecutionClass='FLEX'|'STANDARD'
        #)
        #return response

def main():
    print("Aws Py Console - Glue Job START")
    o=AwsGlueJob("default")
    l=o.jobs_list()
    print("-----------")
    for t in l:
        print(t)
    print("-----------")
    if len(l) > 0:
        print ( o.job_detail( l[0]["Name"]) )
        e=o.job_execution_list( l[0]["Name"])
        if len(e)>0:
            print("-----------")
            print(e[0])
            print("-----------")
            r=o.job_execution_detail( l[0]["Name"] , e[0]["Id"] )
            print( r )
    print("----------- END")


if __name__ == '__main__':
    main()



