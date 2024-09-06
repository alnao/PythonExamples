from pyspark.sql import *
import os
"""
Actions: collect, count, describe, first, foreach, head, show, summary, tail, take, toLocalIterator
Transform: agg, alias, coalesce, crosstab, distinct, drop, exceptAll, groupBy, join, limit, orderBy, randomSplit,
Transform: select,sort, subtract, transorm, union, unionAll, unionByName, where, withColumn, withColumnRenamed
Methods: cache, explain, hint, createGlobalTempView, isLocal, persist, printSchema, toDF, toJson, writeTo

"""

def crea_data_frame(path):
    spark = SparkSession.builder.appName("PySpark Test").getOrCreate()
    df=spark.read.csv(path,header="true",inferSchema="true",sep=";")
    # alernativa df=spark.read.format("csv").option("header","true").option("inferSchema","true").load("C:\Temp\test.csv")
    print("DF originale")
    df.show(3)
    print("DF con colonna modificata")
    df2=df.withColumnRenamed("colo4","quarta_colonna")
    df2.show(3)
    df.createGlobalTempView("nome_servizio")
    print("DF calcolato con query SQL")
    df3=spark.sql("SELECT * FROM global_temp.nome_servizio where secondacol > 42 ")
    df3.show(3)
    print("DF calcolato trasformazioni spark")
    df4=df.where("coltre is not null").where("secondacol < 42").select("coltre","colonnauno").distinct()
    print( df4.count() )
    df4.show(3)
    print("DF calcolato trasformazioni spark con group by ")
    df5=df.where("coltre is not null").groupBy("colonnauno").count().orderBy("count",ascending=True)
    df5.show()


if __name__ == '__main__':
    if os.path.exists("C:\\Temp\\test.csv"):
        crea_data_frame("C:\\Temp\\test.csv")
    else:
        print("File non trovato")
