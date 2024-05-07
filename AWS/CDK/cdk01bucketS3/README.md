# CDK01 BucketS3
Esempio base per la creazione di un bucket

## Comandi per la creazione del progetto
```
mkdir Cdk01-bucketS3
cd Cdk01-bucketS3
cdk init app --language python
python3 -m pip install -r requirements.txt
python3 -m venv .venv
cdk bootstrap
```

## Comandi usati per il rilascio 
```
cdk ls
cdk synth > BucketS3-template.yaml
cdk deploy      
```


Log:
```
Cdk01BucketS3Stack | 0/4 | 14:53:23 | UPDATE_IN_PROGRESS   | AWS::CloudFormation::Stack | Cdk01BucketS3Stack User Initiated
Cdk01BucketS3Stack | 0/4 | 14:53:26 | CREATE_IN_PROGRESS   | AWS::S3::Bucket    | 01BucketS3 (01BucketS3FB71414A) 
Cdk01BucketS3Stack | 0/4 | 14:53:26 | UPDATE_IN_PROGRESS   | AWS::CDK::Metadata | CDKMetadata/Default (CDKMetadata)
Cdk01BucketS3Stack | 1/4 | 14:53:27 | UPDATE_COMPLETE      | AWS::CDK::Metadata | CDKMetadata/Default (CDKMetadata)
Cdk01BucketS3Stack | 1/4 | 14:53:27 | CREATE_IN_PROGRESS   | AWS::S3::Bucket    | 01BucketS3 (01BucketS3FB71414A) Resource creation Initiated
Cdk01BucketS3Stack | 2/4 | 14:53:50 | CREATE_COMPLETE      | AWS::S3::Bucket    | 01BucketS3 (01BucketS3FB71414A) 
Cdk01BucketS3Stack | 3/4 | 14:53:51 | UPDATE_COMPLETE_CLEA | AWS::CloudFormation::Stack | Cdk01BucketS3Stack 
Cdk01BucketS3Stack | 4/4 | 14:53:51 | UPDATE_COMPLETE      | AWS::CloudFormation::Stack | Cdk01BucketS3Stack 
```

## Comando verifica bucket 
```
aws s3 ls
aws s3 ls cdk-01-bucket-s3
aws cloudformation list-stack-resources --stack-name Cdk01BucketS3Stack --output text
aws cloudformation get-template --stack-name Cdk01BucketS3Stack

```

## Comando per confronto tra sviluppo e ambiente 
```
cdk diff 
```

## Comando per la distruzione
```    
cdk destroy
```


## AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [alnao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*




# Welcome to your CDK Python project!

This is a blank project for CDK development with Python.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
