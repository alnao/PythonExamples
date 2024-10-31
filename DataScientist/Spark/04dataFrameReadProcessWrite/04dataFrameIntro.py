from pyspark.sql import *
from pyspark import SparkConf
from utils.log4j import Log4j
from utils.utils import get_spark_app_config
import os

"""
Per eseguire questo script necessario avere spark.conf, log4j.properties e cartella utils
"""

def read_data(file):
    #data_frame = spark.read.options(header=True, delimiter=";").csv('s3://' + args['bucket'] + "/file.csv")
    data_frame = spark.read.options(header=True, delimiter=";").csv(file)
    return data_frame

def process_data(data_frame):
    data_frame=data_frame.where("Age > 40").select("name","age")
    return data_frame

def process_data_count_by_age(data_frame):
    data_frame=data_frame.select("name","age").groupBy("age").count()
    return data_frame

def write_data(data_frame,file):
    data_frame.show()
    #data_frame.select("*").toPandas().to_csv(PREFIX +'/file.csv' % submission_id, index = False, header=True, sep =';')


if __name__=="__main__":
    conf=get_spark_app_config()
    spark=SparkSession.builder.config(conf=conf).getOrCreate()  #.appName("AlNaoS").master("local[3]").getOrCreate()
    logger=Log4j(spark)
    logger.info("SparkSession started")
    conf_out=spark.sparkContext.getConf()
    logger.error(conf_out.toDebugString() )

    #select data file in & out
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    parent2_dir = os.path.dirname(parent_dir)
    pandas_dir = os.path.join(parent2_dir, "Pandas")
    data_file = os.path.join(pandas_dir, "08data.csv")
    data_file_out = os.path.join(current_dir, "dataout.csv")

    #call read-process-write
    data_frame = read_data(data_file)
    #data_frame = process_data(data_frame)
    data_frame = process_data_count_by_age(data_frame)
    write_data(data_frame,data_file_out)

    logger.debug("SparkSession ending")
    spark.stop()



