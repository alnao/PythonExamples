from flask import Flask, render_template,session , send_file ,redirect , request, url_for, g , flash
from flask_session import Session
import sys
import os
import json
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
#parent_directory = os.path.abspath('..')
#parent_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.append( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) )
from SDK.bucketS3 import AwsBucketS3
from SDK.profiles import AwsProfiles
from SDK.cloud_front import AwsCloudFront
from SDK.ssm_parameter  import AwsSSMparameterStore
from SDK.lambda_function import AwsLambda
from SDK.event_bridge import AwsEventBridge
from SDK.step_function import AwsStepFunction

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

# cloufFront_invalid
@app.route('/cloudFront') 
def service_cloudFront(): 
    cf=AwsCloudFront( session.get("profile") ) 
    session["list_cf"]=cf.list_distributions() #print(e['Id'] + "|" + e['Status'] + "|" + e['Origins']['Items'][0]['DomainName'])
    return render_template("services/cloudFront.html", profile=session.get("profile"), list_cf=session["list_cf"] , list_invalidaz=[] , load_l2=False)

@app.route('/cloufFront_level2/<dist>') 
def service_cloudFront_level2(dist): 
    cf=AwsCloudFront( session.get("profile") ) 
    dettaglio=cf.get_distribution(dist)
    invalidaz=cf.get_invalidations(dist)
    return render_template("services/cloudFront.html", profile=session.get("profile"), sfsel=dist, list_cf=session["list_cf"], dettaglio=dettaglio, list_invalidaz=invalidaz , load_l2=True)

@app.route('/cloufFront_invalid/<dist>') 
def service_cloufFront_invalid(dist): 
    cf=AwsCloudFront( session.get("profile") ) 
    cf.invalid_distribuzion(dist)
    session["list_cf"]=cf.list_distributions()
    return service_cloudFront_level2(dist)

# ssm_parameter_store
@app.route('/ssm_parameter_store') 
def ssm_parameter_store(): 
    ssmps=AwsSSMparameterStore( session.get("profile") ) 
    session["list_ssmps"]=ssmps.get_parameters_by_path("/")
    return render_template("services/ssm_ps.html", profile=session.get("profile"), list=session["list_ssmps"] , load_l2=False)

@app.route('/ssm_parameter_store/<parametro>') 
def ssm_parameter_store_level2(parametro): 
    parametro=parametro.replace("ç","/")
    dettaglio=[]
    for l in session["list_ssmps"]:
        if l["Name"]==parametro:
            dettaglio=l
    return render_template("services/ssm_ps.html", profile=session.get("profile"), list=session["list_ssmps"] ,dettaglio=dettaglio , parametro=parametro, load_l2=True)

@app.route('/ssm_parameter_store_update', methods = ['POST'])   
def ssm_parameter_store_update():    #see https://www.geeksforgeeks.org/how-to-upload-file-in-python-flask/
    if request.method == 'POST':   
        parametro  = request.form.get('parametro')
        text  = request.form.get('text')
        ssmps=AwsSSMparameterStore( session.get("profile") ) 
        ssmps.put_parameter(parametro, text , "String" , parametro )
        session["list_ssmps"]=ssmps.get_parameters_by_path("/")
        return ssm_parameter_store_level2(parametro)
    flash('Nothing to do')
    return index()

@app.route('/lambda') 
def service_lambda(): 
    l=AwsLambda( session.get("profile") ) 
    session["list"]=l.list_functions()
    session["list"]=sorted(session["list"], key=lambda tup: tup["Name"])
    return render_template("services/lambda.html", profile=session.get("profile"), list=session["list"] ,lsel='', detail=[],logs=[] , load_l2=False)

@app.route('/lambda_level2/<function_name>') 
def service_lambda_level2(function_name): 
    l=AwsLambda( session.get("profile") ) 
    d=l.get_function(function_name)
    s=l.get_statistic(function_name)
    logs=l.get_logs(function_name)
    for l in logs:
        l["timestamp"]=datetime.fromtimestamp( l['timestamp'] /1000 )
        l["timestamp"]=l["timestamp"].strftime("%m-%d %H:%M:%S")
    return render_template("services/lambda.html", profile=session.get("profile"), list=session["list"] 
                        ,lsel=function_name, dettaglio=d,statistiche=s,logs=logs , load_l2=True)

# event_bridge
@app.route('/event_bridge') 
def event_bridge(): 
    eb=AwsEventBridge( session.get("profile") ) 
    session["list_eb"]=eb.list("")
    return render_template("services/eventBridge.html", profile=session.get("profile"), list=session["list_eb"] , load_l2=False)
# event_bridge
@app.route('/event_bridge/<name>') 
def event_bridge_detail(name): 
    eb=AwsEventBridge( session.get("profile") ) 
    detail=eb.describe_rule(name)
    definition = json.dumps(json.loads(detail['EventPattern']) , indent=2)
    return render_template("services/eventBridge.html", profile=session.get("profile"), list=session["list_eb"] , detail=detail, load_l2=True , sel=name , definition=definition)


# step_function
@app.route('/step_function') 
def step_function(): 
    sf=AwsStepFunction( session.get("profile") ) 
    session["list_sf"]=sf.state_machine_list()
    return render_template("services/stepFunction.html", profile=session.get("profile"), list=session["list_sf"] , load_l2=False)
@app.route('/step_function/<arn>') 
def step_function_detail(arn): 
    sf=AwsStepFunction( session.get("profile") ) 
    detail=sf.state_machine_detail(arn)
    detail2=sf.state_machine_execution(arn)
    #definition=json.dumps(detail['definition']).replace("\\n","\n").replace("\\\"","\"")[1:-1]
    definition = json.dumps(json.loads(detail['definition']) , indent=2)
    return render_template("services/stepFunction.html", profile=session.get("profile"), list=session["list_sf"] , detail=detail, detail2=detail2,load_l2=True , sel=arn, definition=definition)





if __name__ == '__main__': 
    #app.run() 
    app.run(host='0.0.0.0', port=8001, debug=True ) #, ssl_context=("./localCert/cert.pem", "./localCert/key.pem") )
    
    