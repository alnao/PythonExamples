import configparser
from pyspark import SparkConf

def get_spark_app_config():
    spark_conf=SparkConf()
    config=configparser.ConfigParser()
    config.read("spark.conf")
    for (key,value) in config.items("SPARK_APP_CONF"):
        spark_conf.set(key,value)
    return spark_conf