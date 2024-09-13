from pyspark.sql import *
#from pyspark.sql.functions import lit, length, col, monotonically_increasing_id, count, collect_set, concat_ws, trim, upper, size, split, coalesce, array_contains, to_date
from pyspark.sql.functions import col ,date_format,to_date,length


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

def validate_date(): #https://sparkbyexamples.com/pyspark/pyspark-sql-date-and-timestamp-functions/
    spark = SparkSession.builder.appName('SparkByExamples.com').getOrCreate()
    anagrafica_list=[["1","01/02/2024"],["2","16/42/1984"],["3",""],["4","1323123"],["5","16/10/1984"]]
    anagrafica=spark.createDataFrame(anagrafica_list,["id","date"])
    #df.show()
    anagrafica_date_cast=anagrafica.select(
        col("id"),col("date"),#NO date_format(col("date"), "dd/MM/yyyy").alias("date_format") 
        to_date(col("date").cast("string"), "dd/MM/yyyy").alias('date_cast')  #https://stackoverflow.com/questions/66750765/conver-int-yyyymmdd-to-date-pyspark
    )
    #anagrafica_date_cast.show()
    anagrafica_date_cast_error=anagrafica_date_cast.filter(col("date_cast").isNull() & (length(col("date")) > 0) )
    anagrafica_date_cast_error.show()

    #spark.stop()

if __name__ == '__main__':
    validate_date()