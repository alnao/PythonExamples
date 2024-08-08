from pyspark.sql import *

"""
Per funzionare pySpark
1) installare java (8 o 11, la 17 e successive non funzionano)
2) installare python (3.6+)
3) scaricare "hadoop winutils" python da https://github.com/cdarlint/winutils 
3b) configurare le variabili d'ambiente HADOOP_HOME (senza bin) e PATH (con la bin del punto precedente) 
4) scaricare spark da https://spark.apache.org/downloads.html
4b) configurare le variabili d'ambiente SPARK_HOME (senza bin) e PATH (con la bin del punto precedente) 
5) testare lanciando il comando da riga di comando "pyspark"
6) configurare le variabili d'ambiente PYSPARK_PYTHON e PYSPARK_DRIVER_PYTHON con il path dell'eseguibile py oppure vedere sotto
"""

#import os #https://stackoverflow.com/questions/55559763/spark-not-executing-tasks
#os.environ['PYSPARK_PYTHON'] = 'C:\\ProgrammiDev\\Python311\\python.exe' # Worker executable
#os.environ['PYSPARK_DRIVER_PYTHON'] = 'C:\\ProgrammiDev\\Python311\\python.exe' # Driver executable

if __name__ == '__main__':
    spark=SparkSession.builder\
        .appName("First spark application")\
        .master("local[2]")\
        .getOrCreate()
    data_list=[("Alberto",28),("Andrea",42),("Pietro",76)]
    df=spark.createDataFrame(data_list).toDF("Name","Age")
    df.show()

    