"""Job AWS Glue: legge dal Data Catalog la tabella creata dal crawler sui CSV e scrive le righe in RDS MySQL.

Il job bookmark e' attivo: a ogni esecuzione il job legge solo i file CSV nuovi, quindi un file gia'
caricato non viene inserito di nuovo. La tabella MySQL viene creata da Glue alla prima scrittura.
"""

import logging
import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import col

logger = logging.getLogger()
logger.setLevel(logging.INFO)

args = getResolvedOptions(sys.argv, ["JOB_NAME", "TempDir", "database_name", "table_name",
                                     "rds_connection_name", "rds_database", "rds_table_name"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# tabella del Data Catalog creata dal crawler (nomi delle colonne in minuscolo: cognome, nome, eta)
source = glue_context.create_dynamic_frame.from_catalog(
    database=args["database_name"], table_name=args["table_name"], transformation_ctx="source")
df = source.toDF()
logger.info("righe nuove da caricare: %s", df.count())

if df.count() == 0:
    logger.info("nessun file nuovo (job bookmark): niente da scrivere")
else:
    missing = {"nome", "cognome", "eta"} - set(df.columns)
    if missing:
        raise ValueError(f"colonne mancanti nel CSV: {sorted(missing)} (presenti: {df.columns})")
    cleaned = df.select(col("nome").alias("Nome"), col("cognome").alias("Cognome"), col("eta").cast("int").alias("Eta"))
    cleaned.show(10, truncate=False)
    glue_context.write_dynamic_frame.from_jdbc_conf(
        frame=DynamicFrame.fromDF(cleaned, glue_context, "cleaned"),
        catalog_connection=args["rds_connection_name"],
        connection_options={"dbtable": args["rds_table_name"], "database": args["rds_database"]},
        redshift_tmp_dir=args["TempDir"],
        transformation_ctx="write_to_rds")
    logger.info("scrittura in RDS completata")

job.commit()
