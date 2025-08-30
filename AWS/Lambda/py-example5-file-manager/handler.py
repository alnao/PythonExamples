#import json
#from re import M
import boto3
#import cStringIO
import os
s3=boto3.client('s3');
suff=os.environ['SUFFISSO'];
size=int(os.environ['SIZE']);
destination=os.environ['DESTINATION'];

def s3_copy_generator(event, context):
    #step
    print(event);
    #get file info
    bucket = event['Records'][0]['s3']['bucket']['name'];
    key = event['Records'][0]['s3']['object']['key'];
    #get file file
    obfile = get_file(bucket,key);
    #create th
    th = file_to_th(obfile);
    th_key = new_file_name(key);
    #uload miniature
    url = upload_to_s3(destination, th_key, th);
    return url;

def get_file(bucket,key):
    response =s3.get_object(Bucket=bucket,Key=key);
    content = response['Body'].read();
    return content;
    #file = cStringIO.StringIO(content);
    #img = Image.open(file);
    #return img;

def file_to_th(image):
    #image = ImageOps.fit (image, (size,size) , Image.ANTIALIAS )
    return image;

def new_file_name(key):
    elab = key.split('.',1);
    if len(elab)<2 : 
        elab.append("file");
    return elab[0] + suff + ".file";# + elab[1];

def upload_to_s3(bucket, key, content):
    #out = cStringIO.StringIO();
    #image.save(out,'PNG')
    #out.seek(0);
    response = s3.put_object(
        ACL='public-read',
        Body=content, #out,
        Bucket = bucket,
        ContentType='text/plain',#'image/png',
        Key=key
    );
    print(response);
    url ='{}/{}/{}'.format(s3.meta.endpoint_url, bucket, key);
    return url;
