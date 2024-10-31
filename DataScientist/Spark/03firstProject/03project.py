from pyspark.sql import *
from pyspark import SparkConf
from utils.log4j import Log4j
from utils.utils import get_spark_app_config

"""
Per eseguire questo script necessario avere spark.conf, log4j.properties e cartella utils
"""


#to config log4j.properties check
#echo %SPARK_HOME%  #C:\ProgrammiDev\hadoop-3.3.6\spark-3.5.1-bin-hadoop3\spark-3.5.1-bin-hadoop3
# conf\spark.defaults.conf
# add paramater to log4j.properties with
#spark.driver.extraJavaOptions 	 -Dlog4j.configuration=file:log4j.properties 	-Dspark.yarn.app.container.log.dir=logs-dir 

if __name__=="__main__":
    conf=get_spark_app_config()
    spark=SparkSession.builder.config(conf=conf).getOrCreate()  #.appName("AlNaoS").master("local[3]").getOrCreate()
    logger=Log4j(spark)
    logger.info("SparkSession started")

    conf_out=spark.sparkContext.getConf()
    logger.error(conf_out.toDebugString() )

    logger.debug("SparkSession ending")
    spark.stop()