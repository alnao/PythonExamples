"""
Questo script è creato da ConsoleWeb impostando 
- importante usare spark 3.3 e non successive
- Regola IAM: create regola IAM dedicata con i permessi **MOLTO** larghi:
    - AmazonEC2FullAccess
    - AmazonS3FullAccess
    - AWSGlueConsoleFullAccess
    - CloudWatchLogsFullAccess
- parametri del job
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
- connection (con configurazione VPC, subnets e security group)
- su eventbridge aggiunta l'invocazione al workflow (che poi richiama il job) con anche regola iam dedicata
"""
import boto3
import sys
import logging
import json
import traceback
from datetime import datetime
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *

from py4j.java_gateway import java_import

# Configurazione logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("=== JOB STARTING ===")

def check_s3_file_exists_boto3(s3_path):
    """
    Verifica l'esistenza di un file S3 usando boto3
    
    Args:
        s3_path (str): Path completo S3 (es. 's3://bucket/path/to/file.csv')
        
    Returns:
        bool: True se il file esiste, False altrimenti
    """
    try:
        # Estrai bucket e key dal path S3
        s3_parts = s3_path.replace("s3://", "").split("/", 1)
        bucket = s3_parts[0]
        key = s3_parts[1] if len(s3_parts) > 1 else ""
        
        # Crea client S3
        s3_client = boto3.client('s3')
        
        # Verifica esistenza del file
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise e

def execute_sql(sql_command, connection_options):
    conn = None
    try:
        # Crea connessione JDBC
        conn = spark._sc._jvm.DriverManager.getConnection(
            connection_options['url'],
            connection_options['user'],
            connection_options['password']
        )
        
        # Esegue il comando SQL
        stmt = conn.createStatement()
        stmt.execute(sql_command)
        stmt.close()
        
    except Exception as e:
        print(f"Errore nell'esecuzione SQL: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()



def elabora_file(file_path,full_source_path):
    print("elabora_file",file_path,full_source_path)
    numeri_righe=0
    numero_campi=0
    campi = []
    campi_date=[]
    if file_path.startswith("tabella1"):
        tabella="tabella1"
        campi = ["data_riferimento", "campo1", "campo1"]
        numero_campi=3
        campi_date = ["data_riferimento"]
    if file_path.startswith("dominio"):
        tabella="dominio"
        campi = ["dat_rife", "tabella", "chiave", "descrizione"] 
        campi_date = ["dat_rife"]
        numero_campi=4

    if numero_campi==0:
        print("ERROR: file non riconosciuto:" + file_path)
        raise Error("Tipo di file non riconosciuto " + file_path)
    
    print("tabella",tabella)
    print("campi",campi)
    print("campi_date",campi_date)
    
    # Creare lo schema esplicito
    schema = StructType()
    for campo in campi:
        schema.add(campo, StringType(), True)
        # Per i campi data, usa DateType()
        #if campo in campi_date:
        #    schema.add(campo, DateType(), True)
        #else:
        #    # Per tutti gli altri campi, usa StringType() per mantenerli come stringhe
        #    schema.add(campo, StringType(), True)

    logger.info("About to read CSV file...")
    # Aggiunta opzioni per il debug
    df = spark.read \
        .option("delimiter", "\";\"") \
        .option("header", "false") \
        .option("quote", "\"") \
        .schema(schema) \
        .option("mode", "PERMISSIVE") \
        .option("trace", "true") \
        .csv(full_source_path)
        #.option("inferSchema", "false") \ tolto quando messo schema
    
    logger.info("CSV read completed")
    print("CSV read completed")

    # Sostituisci i null con stringa vuota per tutti i campi non-data
    for column in df.columns:
        if column not in campi_date:
            df = df.withColumn(column, when(col(column).isNull(), "").otherwise(col(column)))

    column_names = campi
    # Rinomina le colonne
    for i, name in enumerate(column_names):
        df = df.withColumnRenamed(f"_c{i}", name)
    
    #Elimino caratteri sporchi        
    if "data_riferimento" in column_names:
        df = df.withColumn("data_riferimento", regexp_replace(col("data_riferimento"), "\"", ""))
    
    # convertire le date
    for column in campi_date:
        df = df.withColumn( column , to_date( column , "yyyy-MM-dd"))
    
    if "password" in df.columns:
        df = df.withColumn("password", lit(""))
        print("Colonna password impostata a stringa vuota")   

    print("tabella righe",str( df.count() ))

    connection_options = {
       "url": f"jdbc:sqlserver://{args['jdbc_host']}:{args['jdbc_port']};databaseName={args['database_name']}",
       "user": args['jdbc_user'],
       "password": args['jdbc_password'],
       "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
       "dbtable": tabella #args['target_table']
    }  
    print("Fermo gli indici ",tabella)
    disable_indexes = f"ALTER INDEX ALL ON {tabella} DISABLE"
    execute_sql(disable_indexes, connection_options)
    
    print("TRUNCATE TABLE ",tabella)
    truncate_sql = f"TRUNCATE TABLE {tabella} " # WITH (TABLOCK)
    execute_sql(truncate_sql, connection_options)
    #execute_sql(f"TRUNCATE TABLE {tabella}", connection_options)

    print("Inizio a scrivere i dati nella tabella ",tabella)
    df.write \
       .format("jdbc") \
       .options(**connection_options) \
       .option("truncate", "false") \
       .option("batchsize", 10000) \
       .option("isolationLevel", "READ_UNCOMMITTED") \
       .option("numPartitions", 10) \
       .mode("append") \
       .save()

       
    # Riabilita gli indici
    print("Ri-creo gli indici ",tabella)
    rebuild_indexes = f"ALTER INDEX ALL ON {tabella} REBUILD"
    execute_sql(rebuild_indexes, connection_options)
    
    print("Processo terminato su " , tabella )
    
try: #START JOB
    print("START JOB" )
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
    
    logger.info(f"Host: {args['jdbc_host']}")

    logger.info("Initializing Spark context...")
    sc = SparkContext.getOrCreate()
    logger.info("Created Spark Context")
    
    glueContext = GlueContext(sc)
    logger.info("Created Glue Context")
    
    spark = glueContext.spark_session
    logger.info("Got Spark Session")
    java_import(spark._sc._jvm, "java.sql.DriverManager")
    
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    logger.info("Job initialized")

    data_oggi = datetime.now().strftime('%Y%m%d')
    lista=[
        "tabella1_"+data_oggi+".csv",
        "dominio_"+data_oggi+".csv",
    ]
    for file_dwh in lista:
        file_s3="s3://bucket/" + file_dwh
        exists_boto3 = check_s3_file_exists_boto3(file_s3)
        if exists_boto3:
            try:
                elabora_file(file_dwh, file_s3)
            except Exception as e:
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            print("File non trovato " + file_s3)
    
    job.commit()
    print("job.commit()")
except Exception as e:
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Error message: {str(e)}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    job.commit()
    print("job.commit()")
    raise e
finally:
    logger.info("=== JOB ENDED ===")