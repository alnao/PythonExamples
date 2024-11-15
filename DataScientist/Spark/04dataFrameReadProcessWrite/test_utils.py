from unittest import TestCase
from pyspark.sql import SparkSession
from dataFrameReadProcessWrite import read_data, process_data_count_by_age,get_file_path,get_spark_app_config
import os

"""
Per eseguire questi unit test sui metodi read_data e process_data_count_by_age lanciare il comando
python -m unittest test_utils.py
"""

class UtilsTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        conf=get_spark_app_config() # .master("local[3]") \
        cls.spark=SparkSession.builder \
                .appName("DataFrameReadProcessWrite") \
                .config(conf=conf).getOrCreate()
        print("setUpClass")
    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()
    
    def test_read_data(self):
        data_file,data_file_out=get_file_path()
        #data_file_out = os.path.join(current_dir, "dataout.csv")
        sample_df=read_data(self.spark,data_file)
        result_count=sample_df.count()
        self.assertEqual(result_count,9,"Record count should be 9")

    def test_process_data_count_by_age(self):
        data_file,data_file_out=get_file_path()
        sample_df=read_data(self.spark, data_file)
        count_dict=dict()
        count_list=process_data_count_by_age(sample_df).collect()
        for row in count_list:
            count_dict[row["age"]]=row["count"]
        self.assertEqual(count_dict["42"],1,"Record 42 count should be 1")
        self.assertEqual(count_dict["76"],2,"Record 76 count should be 2")


        

        
#read_data
#process_data_count_by_age