import zipfile
import io
import os
import fnmatch
from io import BytesIO
from boto3 import resource

#see examples
#  https://stackoverflow.com/questions/3451111/unzipping-files-in-python
#  https://betterprogramming.pub/unzip-and-gzip-incoming-s3-files-with-aws-lambda-f7bccf0099c9

def unzip_files(source_file, dest_dir):
    with zipfile.ZipFile(source_file, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)

print("Unzip file start")
unzip_files("/mnt/Dati/daSmistare/daSmistare.zip", "/mnt/Dati/daSmistare/toDEL/prova/")
print("Unzip file end")
