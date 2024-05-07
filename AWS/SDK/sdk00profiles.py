import boto3
s3 = boto3.resource('s3')

class AwsProfiles:
    def __init__(self):
        self.lista_profili=boto3.session.Session().available_profiles
    
    def get_lista_profili(self):
        return self.lista_profili

    def get_lista_bucket_default(self):
        list=s3.buckets.all()
        return list

def main():
    p=AwsProfiles()
    print("Aws Py Console - Profiles START")
    lista_profili=p.get_lista_profili()
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


