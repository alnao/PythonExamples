import boto3


class AwsProfiles:
    def __init__(self):
        self.lista_profili=boto3.session.Session().available_profiles
        self.session=None
    
    def get_lista_profili(self):
        return self.lista_profili
    
    def set_active_profile(self,profile):
        self.session= self.lista_profili=boto3.session.Session( profile_name = profile )
        return self.session

    def get_lista_bucket_default(self):
        s3_client = boto3.resource("s3")
        list=s3_client.buckets.all()
        return list

def main():
    p=AwsProfiles()
    print("Aws Py Console - Profiles START")
    lista_profili=p.get_lista_profili()
    print("------------------")
    print("Set default profile")
    client=p.set_active_profile("default")
    print("------------------")
    print("lista profili:")
    for profilo in lista_profili:
        print(profilo)
    print("------------------")
    print("lista bucket:")
    for bucket in p.get_lista_bucket_default():
        print(bucket.name)
    print("------------------")
    print("Aws Py Console - Profiles END")

if __name__ == '__main__':
    main()
    #boto3.client('sts').get_caller_identity()

