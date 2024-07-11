import boto3
#import os

class AwsApiGateway:
    def __init__(self, profile_name):
        self.profile_name=profile_name
           
    def api_list(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        client = boto3.client('apigateway')
        response = client.get_rest_apis(       limit=100    )
        if 'items' in response:
            return response['items']
        return []

    def resouce_list(self,api_ip):
        client = boto3.client('apigateway')
        response = client.get_resources(        restApiId=api_ip,        limit=100)
        if 'items' in response:
            return response['items']
        return []

    def method_detail(self,api_ip,resouce_id,method):
        client = boto3.client('apigateway')
        response = client.get_method(restApiId=api_ip,resourceId=resouce_id,httpMethod=method)
        return response

    def stage_list(self,api_ip):
        client = boto3.client('apigateway')
        response = client.get_stages(        restApiId=api_ip)
        if 'item' in response:
            return response['item']
        return response

def main(profile):
    print("Aws Py Console - AwsBucket START")
    o = AwsApiGateway(profile)
    l=o.api_list()
    for e in l:
        print(e['id'] + "|" + e['name'] + "|" + str(e['createdDate']) )
    if len(l)>0:
        print("--------")
        d=o.resouce_list(l[0]['id'])
        for e in d:
            print(e)
        if len(d)>0:
            print("--------")
            if 'GET' in d[0]['resourceMethods']:
                m=o.method_detail(l[0]['id'],d[0]['id'],'GET' )
                print(m)
        print("--------")
        s=o.stage_list(l[0]['id'])
        for e in s:
            print(e)
        print("--------")

if __name__ == '__main__':
    main("default")