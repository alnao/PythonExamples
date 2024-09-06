import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.types import StructField
from pyspark.sql.types import StructType
from pyspark.sql.types import StringType

"""
Comandi AWS-CLI per creare ed eseguire lo script
* Deploy del file python 
    ```
    aws s3 cp ./example01console.py s3://formazione-alberto/CODE/glue/example01console.py
    ```
* Creazione regola IAM
    ```
	aws iam create-role --role-name glue-esempio01-role --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"glue.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
    aws iam put-role-policy --role-name glue-esempio01-role --policy-name WriteToBucket_policy --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"s3:*\",\"Resource\":[\"arn:aws:s3:::*\",\"arn:aws:s3:::*/*\"]}]}"
    ```
* Creazione un nuovo job:
    ```
    aws glue create-job --name glue-esempio01 --role glue-esempio01-role --command Name=glueetl,PythonVersion=3,ScriptLocation=s3://formazione-alberto/CODE/glue/example01console.py
    ```
* Elenco i jobs:
    ```
    aws glue get-jobs --query Jobs[*].[Name,Command.ScriptLocation,ExecutionClass] --output table
    ```
* Avvio di un job
    ```
    aws glue start-job-run --job-name glue-esempio01
    ```
* Dettaglio di una esecuzione di un job 
    ```
    aws glue get-job-runs --job-name glue-esempio01
    aws glue get-job-runs --job-name glue-esempio01 --query JobRuns[*].[StartedOn,JobRunState,CompletedOn] --output table
    aws glue get-job-run --job-name glue-esempio01 --run-id jr_xxx  --query JobRun[StartedOn,JobRunState,CompletedOn] --output table
    ```
* Eliminare un job:
    ```
    aws glue delete-job --job-name glue-esempio01
    aws iam delete-role-policy --role-name glue-esempio01-role --policy-name WriteToBucket_policy
    aws iam delete-role --role-name glue-esempio01-role
    ```
"""
bucket="formazione-alberto"
path_in="/INPUT/prova.csv"
path_out="/OUTPUT/prova_out.csv"

# start job with spark
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)
schemaString = "numero lettera lungo gruppo"

#manage data and read input file 
fields = StructType( [StructField(field_name, StringType(), True) for field_name in schemaString.split()] )
FILECSV = spark.read.format("csv").schema(fields).option("delimiter",";").option("header","true").load("s3://"+bucket+path_in)
FILECSVfilter = FILECSV.filter("gruppo == 'A'")
column=[ field_name for field_name in schemaString.split() ]

#write output file
FILECSVdf=FILECSVfilter.toDF( *column )
FILECSVdf.write.format("csv").option("quote", None).option("delimiter",";").option("header","true").mode("append").save("s3://"+bucket+path_out)

#end glue job
job.commit()
