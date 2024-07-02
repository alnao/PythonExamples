import boto3
from time import time
#see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront/client/list_invalidations.html
    #see https://gist.github.com/jolexa/e58ea2ec19cf3067d0ddfbdc98bbaf6d

class AwsCloudFront:

    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.client = boto3.client('cloudfront')
        boto3.setup_default_session(profile_name=self.profile_name)

    def list_distributions(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        response = self.client.list_distributions(MaxItems='200')  
        if 'DistributionList' in response:
            if 'Items' in response['DistributionList']:
                return response['DistributionList']['Items'] #['ResponseMetadata']
        return []

    def get_distribution(self,distribution_id):
        boto3.setup_default_session(profile_name=self.profile_name)
        response = self.client.get_distribution(Id=distribution_id)  
        return response['Distribution'] #['ResponseMetadata']

    def get_invalidations(self,distribution_id):
        boto3.setup_default_session(profile_name=self.profile_name)
        response = self.client.list_invalidations( DistributionId=distribution_id )
        if "InvalidationList" in response:
            if "Items" in response["InvalidationList"]:
                return response["InvalidationList"]["Items"]
        return []
    #see https://gist.github.com/jolexa/e58ea2ec19cf3067d0ddfbdc98bbaf6d
    def invalid_distribuzion(self, distribution_id):
        response = self.client.create_invalidation(
            #DistributionId=get_id(sys.argv[1]),
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': [
                        '/*'
                        ],
                    },
                'CallerReference': str(time()).replace(".", "")
                }
            )
        return response
    

def main():
    print("Aws Py Console - CloudFront START")
    ser=AwsCloudFront("default")
    l=ser.list_distributions()
    for e in l:
        print(e['Id'] + "|" + e['Status'] + "|" + e['Origins']['Items'][0]['DomainName'])
    print("----------------------------------------------------------------")
    if len(l)>0:
        d=ser.get_distribution(l[0]['Id'])
        print(d)
    print("----------------------------------------------------------------")
    element="E2ENONHH3I7XUE"
    l=ser.get_invalidations(element)
    if len(l)>0:
        for e in l:
            print (e)
    print("----------------------------------------------------------------")
    #res=ser.invalid_distribuzion(element)
    #print (res)
    print("----------------------------------------------------------------")
    l=ser.get_invalidations(element)
    if len(l)>0:
        for e in l:
            print (e)
    print("----------------------------------------------------------------")
    

if __name__ == '__main__':
    main()