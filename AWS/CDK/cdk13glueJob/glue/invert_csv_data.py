import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import desc

# Inizializza il job Glue
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'source_path', 'destination_path'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Leggi il CSV di input con separatore punto e virgola
inputDF = spark.read.option("header", "true").option("sep", ";").csv(args['source_path'])

# Inverti l'ordine delle righe basandosi su tutte le colonne
invertedDF = inputDF.orderBy(*[desc(c) for c in inputDF.columns])

# Scrivi il risultato nel percorso di destinazione con separatore punto e virgola
invertedDF.write.mode("overwrite").option("header", "true").option("sep", ";").csv(args['destination_path'])

# Completa il job
job.commit()