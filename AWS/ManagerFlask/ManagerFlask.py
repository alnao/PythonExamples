from flask import Flask, render_template,session , send_file ,redirect , request, url_for, g , flash
from flask_session import Session
import sys
import os
import base64
from werkzeug.utils import secure_filename
#parent_directory = os.path.abspath('..')
#parent_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) )
from SDK.sdk01bucketS3 import AwsBucketS3
from SDK.sdk00profiles import AwsProfiles

app = Flask(__name__) 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 #see https://blog.miguelgrinberg.com/post/handling-file-uploads-with-flask
UPLOAD_FOLDER="/tmp/"
if os.path.exists("C:\\temp\\"):
    UPLOAD_FOLDER = 'C:\\temp\\'
app.config['UPLOAD_PATH'] = UPLOAD_FOLDER
app.config["SESSION_FILE_DIR"] = UPLOAD_FOLDER + "flask_session"

Session(app) #https://www.geeksforgeeks.org/how-to-use-flask-session-in-python-flask/

@app.route('/') 
def index(): 
    if session.get("profile")==None:
        session["profile"]="default"
    return render_template("index.html")

@app.route('/profili') 
def service_profiles():
    pro=AwsProfiles()
    list=pro.get_lista_profili()
    return render_template("services/profiles.html", profile=session.get("profile"), list=list)

@app.route('/profili/<profile>')
def service_profiles_set(profile):
    session["profile"]=profile
    return service_profiles()

@app.route('/s3') 
def service_s3(): 
    s3=AwsBucketS3( session.get("profile") ) 
    list_s3=s3.bucket_list()
    session["list_s3"]=list_s3
    return render_template("services/s3.html", profile=session.get("profile"), list_s3=list_s3 , load_l2=False,load_l3=False)

@app.route('/s3_level2/<bucket>') 
def service_s3_level2(bucket): 
    s3=AwsBucketS3( session.get("profile") ) 
    list_s3=session.get("list_s3")
    list_object2=s3.object_list(bucket,"")
    return render_template("services/s3.html", profile=session.get("profile"), 
        list_s3=list_s3 , load_l2=True,load_l3=False , bucket=bucket,list_object2=list_object2 )

@app.route('/s3_level3/<bucket>/<path>') 
def service_s3_level3(bucket,path): 
    path=path.replace("ç","/")
    s3=AwsBucketS3( session.get("profile") ) 
    list_s3=session.get("list_s3")
    list_object2=s3.object_list(bucket,"")
    list_object3=s3.object_list(bucket,path)
    return render_template("services/s3.html", profile=session.get("profile"), 
        list_s3=list_s3 , load_l2=True,load_l3=True , bucket=bucket,list_object2=list_object2,list_object3=list_object3,path=path )

@app.route('/s3_download/<bucket>/<path>/<key>') 
def service_s3_download(bucket,path,key): 
    key=key.replace("ç","/")
    s3=AwsBucketS3( session.get("profile") ) 
    url=s3.content_object_presigned(bucket, key)
    return redirect(url) #send_file(url, as_attachment=True)
    #os.system("start \"\" "+url) # urllib2.urlopen(url)
    #if path=="ç":
    #    return service_s3_level2(bucket)
    #else:
    #    return service_s3_level3(bucket,path)

@app.route('/s3_upload', methods = ['POST'])   
def service_s3_upload():    #see https://www.geeksforgeeks.org/how-to-upload-file-in-python-flask/
    if request.method == 'POST':   
        if 'file' not in request.files:
            flash('No file part')
            return index()
        uploaded_file  = request.files['file'] 
        file_name = secure_filename(uploaded_file.filename)
        local_file_name=os.path.join(app.config['UPLOAD_PATH'], file_name) #see https://blog.miguelgrinberg.com/post/handling-file-uploads-with-flask
        uploaded_file.save( local_file_name )
        bucket=request.form.get('bucket')
        path=request.form.get('path')
        if path=="ç":
            dest_path=""
        else:
            dest_path=path.replace("ç","/")
        s3=AwsBucketS3( session.get("profile") ) 
        s3.write_file( bucket , dest_path + uploaded_file.filename , local_file_name ) #write_file(self,bucket_name,key,local_path)
        if path=="ç":
            return service_s3_level2(bucket)
        else:
            print(path)
            return service_s3_level3(bucket,path)
    flash('Nothing to do')
    return index()

if __name__ == '__main__': 
    #app.run() 
    app.run(host='0.0.0.0', port=8001, debug=True ) #, ssl_context=("./localCert/cert.pem", "./localCert/key.pem") )
    
    