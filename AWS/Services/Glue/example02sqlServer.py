import sys
import logging
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *

"""
Questo script legge un file csv posizionato in un S3 e inserisce dati in un dastabse sqlserver su RDS
Si intende che venga creato da console web

- Creato job "UAT Sqlserver load data"
- Regola IAM: create regola IAM "UAT-Sqlserver-glue-iam-role" con i permessi **MOLTO** larghi:
    - AmazonEC2FullAccess
    - AmazonS3FullAccess
    - AWSGlueConsoleFullAccess
    - CloudWatchLogsFullAccess
- Security group: creato security group con regole
    - incoming da se-stesso su tutte le porte TCP
    - incoming da porta 1433
    - outgoing aperto 
- Glue -> "Data Catalog" -> Connection -> "Create connection" impostando il suo RDS, la sua VPN e il security group
- Configura: nelle configurazioni del job bisogna impostare la connessione nella sezione "Current connections"
- Parametri del job:
    --connection_name = "UAT Sqlserver connection"
    --database_name = uat
    --default_source_path = s3://bucket-name/file.csv
    --jdbc_host = 
    --jdbc_password = 
    --jdbc_port =
    --jdbc_user =
    --spark.driver.cores = 2
    --spark.driver.memory = 5g
    --spark.executor.memory = 5g
    --target_table = dbo.nome_tabella
- Comandi AWS-CLI per creare ed eseguire lo script
    todo

"""


# Configurazione logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("=== JOB STARTING ===")

try:
    logger.info("Getting job arguments...")
    required_params = [
        'JOB_NAME',
        'target_table',
        'database_name',
        'jdbc_host',
        'jdbc_port',
        'jdbc_user',
        'jdbc_password',
        'default_source_path'
    ]
    args = getResolvedOptions(sys.argv, required_params)
    
    full_source_path="" #args['default_source_path']
    source_path=""
    try:
        event_args = getResolvedOptions(sys.argv, ['event'])
        event = json.loads(event_args['event'])
        source_path = event['detail']['object']['key']
        bucket = event['detail']['bucket']['name']
        full_source_path = f"s3://{bucket}/{source_path}"
        print(f"Using path from event: {full_source_path}")
    except:
        full_source_path = args['default_source_path']
        print(f"Using default path: {full_source_path}")

    
    print(f"Processing file: {full_source_path}")
    logger.info(f"Target table: {args['target_table']}")
    logger.info(f"Database: {args['database_name']}")
    logger.info(f"Host: {args['jdbc_host']}")

    logger.info("Initializing Spark context...")
    sc = SparkContext.getOrCreate()
    logger.info("Created Spark Context")
    
    glueContext = GlueContext(sc)
    logger.info("Created Glue Context")
    
    spark = glueContext.spark_session
    logger.info("Got Spark Session")
    
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    logger.info("Job initialized")

    logger.info("About to read CSV file...")
    # Aggiunta opzioni per il debug
    df = spark.read \
        .option("delimiter", "\";\"") \
        .option("header", "false") \
        .option("quote", "\"") \
        .option("inferSchema", "true") \
        .option("mode", "PERMISSIVE") \
        .csv(full_source_path)
    
    logger.info("CSV read completed")

    connection_options = {
       "url": f"jdbc:sqlserver://{args['jdbc_host']}:{args['jdbc_port']};databaseName={args['database_name']}",
       "user": args['jdbc_user'],
       "password": args['jdbc_password'],
       "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
       "dbtable": args['target_table']
    }  
    
    column_names = ["campo1", "campo2", "campo3", "campo4", "campo5_data"   ]
    
    # Rinomina le colonne
    for i, name in enumerate(column_names):
        df = df.withColumnRenamed(f"_c{i}", name)
        
    # rimuovo i caratteri sporchi come le " da alcuni campi
    df = df.withColumn("campo1", regexp_replace(col("campo1"), "\"", ""))
    
    
    # Ora puoi convertire le date dal formato yyyy-MM-dd al formato date di SqlServer
    df = df.withColumn("campo5_data", to_date("campo5_data", "yyyy-MM-dd"))

    df.write \
       .format("jdbc") \
       .options(**connection_options) \
       .mode("overwrite") \
       .save()
       #ex \  # Cambiato da "append" a "overwrite" .mode("append") \

    job.commit()

except Exception as e:
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Error message: {str(e)}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    raise e
finally:
    logger.info("=== JOB ENDED ===")