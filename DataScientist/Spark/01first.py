from pyspark.sql import *

"""
Per installare pySpark

su piattaforma windows
1) installare java (8 o 11, la 17 e successive non funzionano)
2) installare python (3.6+)
3) scaricare "hadoop winutils" python da https://github.com/cdarlint/winutils 
3b) configurare le variabili d'ambiente HADOOP_HOME (senza bin) e PATH (con la bin del punto precedente) 
4) scaricare spark da https://spark.apache.org/downloads.html
4b) configurare le variabili d'ambiente SPARK_HOME (senza bin) e PATH (con la bin del punto precedente) 
5) testare lanciando il comando da riga di comando "pyspark"
6) configurare le variabili d'ambiente PYSPARK_PYTHON e PYSPARK_DRIVER_PYTHON con il path dell'eseguibile py oppure vedere sotto

su piattaforma GNU Linux , see https://www.machinelearningplus.com/pyspark/install-pyspark-on-linux/
1) installare java (8 o 11, la 17 funziona dalla versione 3.5.1 di spark)
    pacchetto debian "openjdk" alla versione 17 (vedi https://issues.apache.org/jira/browse/SPARK-33772)
2) installare python (3.6+)
    pacchetto python e pip
    pip install pyspark --break-system-packages
3) installare spark
    wget https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz
    tar -xvzf spark-3.5.1-bin-hadoop3.tgz
    sudo mv spark-3.5.1-bin-hadoop3 /opt/spark351
    sudo chmod 777 /opt/spark351
4) configurare variabili ambiente
    pico ~/.bashrc
	    export SPARK_HOME=/opt/spark351
	    export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
    source ~/.bashrc
5) testare comando "pyspark" e lanciare questo script 
"""

#import os #https://stackoverflow.com/questions/55559763/spark-not-executing-tasks
#os.environ['PYSPARK_PYTHON'] = 'C:\\ProgrammiDev\\Python311\\python.exe' # Worker executable
#os.environ['PYSPARK_DRIVER_PYTHON'] = 'C:\\ProgrammiDev\\Python311\\python.exe' # Driver executable


def test_data_list():
    spark=SparkSession.builder\
        .appName("First spark application")\
        .master("local[2]")\
        .getOrCreate()
    data_list=[("Alberto",28),("Andrea",42),("Pietro",76)]
    df=spark.createDataFrame(data_list).toDF("Name","Age")
    df.show()
    #spark.stop()

def test_data_list2():
    spark = SparkSession.builder.appName("PySpark Test").getOrCreate()
    data = [("Alice", 34), ("Bob", 45), ("Cathy", 29)]
    columns = ["Name", "Age"]
    df = spark.createDataFrame(data, columns)
    df.show()
    spark.stop()

if __name__ == '__main__':
    test_data_list()