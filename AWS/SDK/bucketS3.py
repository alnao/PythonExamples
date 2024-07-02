import boto3
import os

class AwsBucketS3:
    def __init__(self, profile_name):
        self.profile_name=profile_name
           
    def bucket_list(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        s3_client = boto3.client("s3")
        return s3_client.list_buckets()["Buckets"]

    def object_list(self,bucket_name,path):
        s3_client = boto3.client("s3")
        response={"objects":[],"folders":[]}
        response["objects"]=[]
        response["folders"]=[]
        if not path:
            #objects = list(bucket.objects.all())
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, Delimiter="/",
            )
            if "Contents" in response:
                response["objects"]=response["Contents"]
            if "CommonPrefixes" in response:
                response["folders"]=response["CommonPrefixes"]
        else:
            #objects = list(bucket.objects.filter(Prefix=path))
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, Delimiter="/",
                Prefix=path,
            )
            if "Contents" in response:
                response["objects"]=response["Contents"]
            if "CommonPrefixes" in response:
                response["folders"]=response["CommonPrefixes"]
        return self.rimuovi_folder_padre(path,response)

    def object_list_paginator(self, bucket_name,path):
        s3_client = boto3.client("s3")
        response={"objects":[],"folders":[]}
        response["objects"]=[]
        response["folders"]=[]
        s3_paginator = s3_client.get_paginator('list_objects_v2')
        #see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/paginator/ListObjectsV2.html
        for page in s3_paginator.paginate(Bucket=bucket_name, Prefix=path, Delimiter='/'): #, StartAfter=start_after):
            if "Contents" in page:
                response["objects"]=response["objects"] + page["Contents"] #sum to append
            if "CommonPrefixes" in page:
                response["folders"]=response["folders"] + page["CommonPrefixes"] #sum to append
        return self.rimuovi_folder_padre(path,response)

    def rimuovi_folder_padre(self, folder_name,list):
        el={}
        to_remove=False
        if "objects" in list:
            for o in list["objects"]:
                if o["Key"]==folder_name or o["Key"]==folder_name+"/" :
                    el=o
                    to_remove=True
        if to_remove:
            list["objects"].remove(el)
        return list

    def content_object_text(self, bucket_name , key):
        s3_client = boto3.client("s3")
        content = s3_client.get_object(Bucket=bucket_name, Key=key)["Body"].iter_lines()
        lista=[]
        for line in content:
            #print(line)
            lista.append(str(line.decode("utf-8")))
        return lista

    def content_object_presigned(self, bucket_name, key):
        s3_client_p = boto3.client('s3',region_name="eu-west-1",config=boto3.session.Config(signature_version='s3v4',))
        response = s3_client_p.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key':key},ExpiresIn=3600)
        return response

    def write_text_file(self, bucket_name, key, body):
        s3_client = boto3.client("s3")
        OUT_string_encoded = body.encode("utf-8")
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=OUT_string_encoded)
        return True

    def write_file(self,bucket_name,key,local_path):
        s3 = boto3.resource('s3')    
        r=s3.Bucket(bucket_name).upload_file(local_path,key)
        return r

    def delete_all_content_folder(self,bucket_name,path): #max 1000 elements deleted
        s3_client = boto3.client("s3")
        objects = s3_client.list_objects(Bucket=bucket_name, Prefix=path)
        i=0
        for object in objects['Contents']:
            s3_client.delete_object(Bucket=bucket_name, Key=object['Key'])
            i=i+1
        s3_client.delete_object(Bucket=bucket_name, Key=path)
        return i

def test(profile,index):
    print("Aws Py Console - S3 START")
    s3=AwsBucketS3(profile)
    print("-----------")
    lista_b=s3.bucket_list()
    for b in lista_b:
        print (b["Name"])
    buck=lista_b[index]["Name"]
    print("----------- " + buck )
    lista_o=s3.object_list(buck,"")
    if "folders" in lista_o:
        for o in lista_o["folders"]:
            print (o["Prefix"]) #folder
    if "objects" in lista_o:
        for o in lista_o["objects"]:
            print (o["Key"] ) #file LastModified, ETag , Size, StorageClass
    folder="INPUT/" # lista_o["folders"][0]["Prefix"] #es "INPUT/"
    print("----------- object_list: " + folder )
    lista_o2=s3.object_list(buck,folder) #lista_o["folders"][0]["Prefix"]
    if "folders" in lista_o2:
        for o in lista_o2["folders"]:
            print (o["Prefix"]) #folder
    if "objects" in lista_o2:
        for o in lista_o2["objects"]:
            print (o["Key"] ) #file LastModified, ETag , Size, StorageClass
    print("----------- paginante: " + folder )
    lista_op=s3.object_list_paginator(buck, folder)
    if "folders" in lista_op:
        for o in lista_op["folders"]:
            print (o["Prefix"]) #folder
    if "objects" in lista_op:
        for o in lista_op["objects"]:
            print (o["Key"] ) #file LastModified, ETag , Size, StorageClass
    f_key="INPUT/prova_py_sdk.txt"
    f_body="Prova1\nriga 2\nprova3"
    print("----------- scrivo il file file " + f_key)
    s3.write_text_file(buck, f_key, f_body)
    print("----------- file " + f_key)
    c=s3.content_object_text(buck, f_key )
    print(c)
    print("----------- prefigned file " + f_key)
    p=s3.content_object_presigned(buck, f_key)
    print(p)
    print("----------- upload bynary file a.xlsx")
    if os.path.exists("C:\\Temp\\a.xlsx"):
        r=s3.write_file(buck,folder+"v.xlsx","C:\\Temp\\a.xlsx")
        print(r)
        print("upload done")
    if os.path.exists("/mnt/Dati/toDEL/a.xlsx"):
        r=s3.write_file(buck,folder+"v.xlsx","/mnt/Dati/toDEL/a.xlsx")
        print(r)
        print("upload done")
    lista_o2=s3.object_list(buck,folder) #lista_o["folders"][0]["Prefix"]
    if "objects" in lista_o2:
        for o in lista_o2["objects"]:
            print (o["Key"] ) #file LastModified, ETag , Size, StorageClass
    print("----------- end main " )

if __name__ == '__main__':
    test("default",8)