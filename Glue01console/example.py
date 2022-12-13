import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.types import StructField
from pyspark.sql.types import StructType
from pyspark.sql.types import StringType
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)
schemaString = "numero lettera lungo gruppo"
fields = StructType( [StructField(field_name, StringType(), True) for field_name in schemaString.split()] )
FILECSV = spark.read.format("csv").schema(fields).option("delimiter",";").option("header","true").load("s3://alberto-input/INPUT/prova.csv")
FILECSVfilter = FILECSV.filter("gruppo == 'A'")
column=[ field_name for field_name in schemaString.split() ]
FILECSVdf=FILECSVfilter.toDF( *column )
FILECSVdf.write.format("csv").option("quote", None).option("delimiter",";").option("header","true").mode("append").save("s3://alberto-input/INPUT/prova_out.csv")
job.commit()