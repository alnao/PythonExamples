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
from SDK.api_gateway import AwsApiGateway
from SDK.dynamo import AwsDynamoDB
from SDK.rds import AwsRds
from SDK.ec2 import AwsEc2
from SDK.glue_job import AwsGlueJob
from SDK.sqs import AwsSqs
from SDK.sns import AwsSns
from SDK.elastic_ip import AwsElasticIp
from SDK.efs import AwsEfs
from SDK.auto_scaling import AwsAutoScaling
from SDK.app_load_balancer import AwsAppLoadBalancer
from SDK.cloud_watch_alarms import AwsCloudWatchAlarm
from SDK.cloud_watch_logs import AwsCloudWatchLogs

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



# api_gateway
@app.route('/api_gateway') 
def api_gateway(): 
    apis=AwsApiGateway( session.get("profile") ) 
    session["list_apis"]=apis.api_list()
    return render_template("services/apiGateway.html", profile=session.get("profile"), list=session["list_apis"] , load_l2=False)
@app.route('/api_gateway/<id>') 
def api_gateway_detail(id): 
    apis=AwsApiGateway( session.get("profile") ) 
    rl=apis.resouce_list(id)
    stag=apis.stage_list(id)
    return render_template("services/apiGateway.html", profile=session.get("profile"), list=session["list_apis"] , detail=rl, detail2=stag,load_l2=True , sel=id)


# dynamo
@app.route('/dynamo') 
def dynamo(): 
    obj=AwsDynamoDB( session.get("profile") ) 
    session["tables"]=obj.table_list()
    return render_template("services/dynamo.html", profile=session.get("profile"), list=session["tables"] , load_l2=False)
@app.route('/dynamo/<id>') 
def dynamo_detail(id): 
    obj=AwsDynamoDB( session.get("profile") ) 
    all=obj.full_scan_table(id)
    header=[]
    if len(all)>0:
        for index,el in enumerate(all[0]):
            if index<6:
                header.append(el)
    #stag=obj.stage_list(id)
    return render_template("services/dynamo.html", profile=session.get("profile"), list=session["tables"] , all=all, header=header, load_l2=True , sel=id)

#rds
@app.route('/rds') 
def rds(): 
    obj=AwsRds( session.get("profile") ) 
    session["rds"]=obj.db_instances_list()
    return render_template("services/rds.html", profile=session.get("profile"), list=session["rds"] , load_l2=False)
@app.route('/rds/<id>') 
def rds_detail(id): 
    detail=[]
    for l in session["rds"]:
        if l['DBInstanceIdentifier']==id:
            detail=l
    return render_template("services/rds.html", profile=session.get("profile"), list=session["rds"] , detail=detail,   load_l2=True , sel=id)


#ec2
def aggiorna_lista_ec2():
    obj=AwsEc2( session.get("profile") ) 
    lista=[]
    i_list=obj.get_lista_istanze()
    for reservation in i_list['Reservations']:
        for istanza in reservation['Instances']:
            nome=''
            if 'Tags' in istanza: #len(istanza.Tags)>0 :
                for tag in istanza['Tags']:#print (tag)
                    if tag['Key']=='Name':
                        nome=tag['Value']
            i=istanza
            i['Nome']=nome
            lista.append(i)
    session["ec2"]=lista
@app.route('/ec2') 
def ec2(): 
    aggiorna_lista_ec2()
    return render_template("services/ec2.html", profile=session.get("profile"), list=session["ec2"] , load_l2=False)
@app.route('/ec2/detail/<id>') 
def ec2_detail(id): 
    detail=[]
    for l in session["ec2"]:
        if l['InstanceId']==id:
            detail=l
    return render_template("services/ec2.html", profile=session.get("profile"), list=session["ec2"] , detail=detail, all=all,  load_l2=True , sel=id)
@app.route('/ec2/start/<id>') 
def ec2_start(id): 
    obj=AwsEc2( session.get("profile") ) 
    obj.start_instance(id)
    aggiorna_lista_ec2()
    return ec2_detail(id)
@app.route('/ec2/stop/<id>') 
def ec2_stop(id): 
    obj=AwsEc2( session.get("profile") ) 
    obj.stop_instance(id)
    aggiorna_lista_ec2()
    return ec2_detail(id)

# glue_job
@app.route('/glue_job') 
def service_glue_job(): 
    gj=AwsGlueJob( session.get("profile") )
    session["list_gj"]=gj.jobs_list() #print(e['Id'] + "|" + e['Status'] + "|" + e['Origins']['Items'][0]['DomainName'])
    return render_template("services/glue_job.html", profile=session.get("profile"), list_gj=session["list_gj"] , list_invalidaz=[] , load_l2=False)

@app.route('/glue_job_level2/<id>') 
def service_glue_job_level2(id): 
    cf=AwsGlueJob( session.get("profile") )
    dettaglio=cf.job_detail(id)
    esecuzioni=cf.job_execution_list(id)
    return render_template("services/glue_job.html", profile=session.get("profile"), idsel=id, list_gj=session["list_gj"], dettaglio=dettaglio, esecuzioni=esecuzioni , load_l2=True)


#sqs
@app.route('/sqs') 
def sqs(): 
    obj=AwsSqs( session.get("profile") ) 
    session["sqs"]=obj.get_sqs_list()
    return render_template("services/sqs.html", profile=session.get("profile"), list=session["sqs"] , load_l2=False, load_l3=False)
@app.route('/sqs/<id>') 
def sqs_detail(id): 
    obj=AwsSqs( session.get("profile") ) 
    detail=[]
    url_sel=""
    for el in session["sqs"]:
        if el.split('/')[-1]==id:
            url_sel=el
    detail = obj.get_queue( url_sel )
    return render_template("services/sqs.html", profile=session.get("profile"), list=session["sqs"] , detail=detail, all=all,  load_l2=True, load_l3=False , sel=id)

@app.route('/sqs_produce', methods = ['POST'])   
def sqs_produce(): 
    if request.method == 'POST':   
        obj=AwsSqs( session.get("profile") ) 
        url_sel=""
        sqs=request.form.get('sqs')
        for el in session["sqs"]:
            if el.split('/')[-1]==sqs:
                url_sel=el
        content = request.form.get('content')
        formatted_json = json.dumps({'messageEvent':content})
        obj.send_queue_message( url_sel, {}, formatted_json )
        return sqs_detail( sqs )
    flash('Nothing to do')
    return index()

@app.route('/sqs_consume/<id>') 
def sqs_consume(id): 
    obj=AwsSqs( session.get("profile") ) 
    detail=[]
    url_sel=""
    for el in session["sqs"]:
        if el.split('/')[-1]==id:
            url_sel=el
    detail = obj.get_queue( url_sel )
    messages=[]
    lista=obj.receive_queue_messages( url_sel )
    for msg in lista:
        if 'Body' in msg:
            msg_body = msg['Body']
        else:
            msg_body = str(msg)
        receipt_handle = msg['ReceiptHandle']
        obj.delete_queue_message( url_sel , receipt_handle)
        messages.append(msg_body)
    return render_template("services/sqs.html", profile=session.get("profile"), list=session["sqs"] , detail=detail, all=all,  load_l2=True, messages=messages, load_l3=True , sel=id)

#sns
@app.route('/sns') 
def sns(): 
    obj=AwsSns( session.get("profile") ) 
    session["sns"]=obj.list_topics()
    return render_template("services/sns.html", profile=session.get("profile"), list=session["sns"] , load_l2=False)
@app.route('/sns/<id>') 
def sns_detail(id): 
    obj=AwsSns( session.get("profile") ) 
    detail=obj.get_topic_attributes(id)
    sub=obj.list_subscriptions(id)
    return render_template("services/sns.html", profile=session.get("profile"), list=session["sns"] , detail=detail, sub=sub,  load_l2=True , sel=id)
@app.route('/sns_send/<id>', methods = ['POST'])   
def sns_send(id):
    if request.method == 'POST':   
        obj=AwsSns( session.get("profile") ) 
        sns=request.form.get('sns')
        content = request.form.get('content')
        formatted_json = json.dumps({'message':content})
        obj.publish_message( sns, formatted_json )
        return sns_detail( sns )
    flash('Nothing to do')
    return index()


#rds
@app.route('/elastic_ip') 
def elastic_ip(): 
    obj=AwsElasticIp( session.get("profile") ) 
    session["elastic_ip"]=obj.get_elastic_addresses()
    return render_template("services/elastic_ip.html", profile=session.get("profile"), list=session["elastic_ip"] , load_l2=False)
@app.route('/elastic_ip/<id>') 
def elastic_ip_detail(id): 
    detail=[]
    for l in session["elastic_ip"]:
        if l['PublicIp']==id:
            detail=l
    return render_template("services/elastic_ip.html", profile=session.get("profile"), list=session["elastic_ip"] , detail=detail, all=all,  load_l2=True , sel=id)



#efs
@app.route('/efs') 
def efs(): 
    obj=AwsEfs( session.get("profile") ) 
    session["efs"]=obj.describe_file_systems()
    return render_template("services/efs.html", profile=session.get("profile"), list=session["efs"] , load_l2=False)
@app.route('/efs/<id>') 
def efs_detail(id): 
    detail=[]
    for l in session["efs"]:
        if l['FileSystemId']==id:
            detail=l
    obj=AwsEfs( session.get("profile") ) 
    d=obj.describe_mount_targets(id)
    detail2={}
    load_l3=False
    if 'MountTargets' in d:
        if len(d['MountTargets'])>0:
            detail2=d['MountTargets'][0]
            load_l3=True
    return render_template("services/efs.html", profile=session.get("profile"), list=session["efs"] , detail=detail, detail2=detail2, load_l2=True,load_l3=load_l3 , sel=id)

#autoScaling
@app.route('/asg') 
def asg(): 
    obj=AwsAutoScaling( session.get("profile") ) 
    session["asg"]=obj.list_asgs()
    return render_template("services/asg.html", profile=session.get("profile"), list=session["asg"] , load_l2=False)
@app.route('/asg/<id>') 
def asg_detail(id): 
    detail=[]
    for l in session["asg"]:
        if l['AutoScalingGroupName']==id:
            detail=l
    obj=AwsAutoScaling( session.get("profile") ) 
    d=obj.describe_asg(id)
    detail2=[]
    load_l3=False
    if 'Instances' in d:
        if len(d['Instances'])>0:
            for e in d['Instances']:
                detail2.append(e)
            load_l3=True
    return render_template("services/asg.html", profile=session.get("profile"), list=session["asg"] , detail=detail, detail2=detail2, load_l2=True,load_l3=load_l3 , sel=id)

#ALB
@app.route('/alb') 
def alb(): 
    obj=AwsAppLoadBalancer( session.get("profile") ) 
    session["alb"]=obj.describe_load_balancers()
    return render_template("services/alb.html", profile=session.get("profile"), list=session["alb"] , load_l2=False)
@app.route('/alb/<id>') 
def alb_detail(id): 
    detail=[]
    for l in session["alb"]:
        if l['LoadBalancerName']==id:
            detail=l
    obj=AwsAppLoadBalancer( session.get("profile") ) 
    d=obj.describe_target_groups(detail['LoadBalancerArn'])
    detail2=[]
    load_l3=False
    for dl in d :
        if 'TargetGroupArn' in dl:
            #for e in dl['TargetGroupArn']:
            ee=obj.describe_target_health( dl['TargetGroupArn'] )
            detail2.append( ee )
            load_l3=True
    return render_template("services/alb.html", profile=session.get("profile"), list=session["alb"] , detail=detail, detail2=detail2, load_l2=True,load_l3=load_l3 , sel=id)

#cw_alarms
@app.route('/cw_alarms') 
def cw_alarms(): 
    obj=AwsCloudWatchAlarm( session.get("profile") ) 
    session["cw_alarms"]=obj.list_alarms()
    return render_template("services/cw_alarms.html", profile=session.get("profile"), list=session["cw_alarms"] , load_l2=False)
@app.route('/cw_alarms/<id>') 
def cw_alarms_detail(id): 
    detail=[]
    for l in session["cw_alarms"]:
        if l['AlarmName']==id:
            detail=l
    obj=AwsCloudWatchAlarm( session.get("profile") ) 
    d=obj.get_alarm_history(detail['AlarmName'])
    detail2=[]
    load_l3=False
    for event in d:
        history = json.loads( event['HistoryData'] )
        oldState=""
        if 'oldState' in history:
            oldState=history['oldState']
        else:
            if 'type' in history:
                oldState=history['type']
        newState=""
        if 'newState' in history:
            newState=history['newState']
        if oldState!="" or newState!="":
            detail2.append( {'event':event,'oldState':oldState,'newState':newState, 'history':history} )
        load_l3=True
    return render_template("services/cw_alarms.html", profile=session.get("profile"), list=session["cw_alarms"] , detail=detail, detail2=detail2, load_l2=True,load_l3=load_l3 , sel=id)

#cw_logs
@app.route('/cw_logs') 
def cw_logs(): 
    obj=AwsCloudWatchLogs( session.get("profile") ) 
    session["cw_logs"]=[]
    l=obj.list_log_groups()
    for dis in l:
        session["cw_logs"].append(dis)
    return render_template("services/cw_logs.html", profile=session.get("profile"), list=session["cw_logs"] , load_l2=False, load_l3=False)

@app.route('/cw_logs/<id>') 
def cw_logs_stream(id): 
    id=id.replace("ç","/")
    obj=AwsCloudWatchLogs( session.get("profile") ) 
    l=obj.list_log_streams(id)
    session["cw_logs_stream"]=[]
    for e in l:
        session["cw_logs_stream"].append(e)
    session["cw_logs_stream"]=sorted( session["cw_logs_stream"] , key=lambda tup: tup["creationTime"] , reverse=True )
    session["cw_logs_stream"]=session["cw_logs_stream"][0:42]
    return render_template("services/cw_logs.html", profile=session.get("profile"), list=session["cw_logs"] , load_l2=True , 
                           detail=session["cw_logs_stream"], load_l3=False, sel=id)

@app.route('/cw_logs/<id>/<stream>') 
def cw_logs_list(id,stream): 
    id=id.replace("ç","/")
    stream=stream.replace("ç","/")
    obj=AwsCloudWatchLogs( session.get("profile") ) 
    l=obj.get_log_events(id,stream)['events']
    session["cw_logs_list"]=[]
    for e in l:
        session["cw_logs_list"].append(e)
    session["cw_logs_list"]=sorted( session["cw_logs_list"] , key=lambda tup: tup["timestamp"] , reverse=True )
    session["cw_logs_list"]=session["cw_logs_list"][0:42]
    return render_template("services/cw_logs.html", profile=session.get("profile"), list=session["cw_logs"] , load_l2=False , 
                           detail=session["cw_logs_list"], load_l3=True, sel=id,stream=stream)




if __name__ == '__main__': 
    #app.run() 
    app.run(host='0.0.0.0', port=8001, debug=True ) #, ssl_context=("./localCert/cert.pem", "./localCert/key.pem") )
    
    