#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/testing.html
from pandas.testing import assert_frame_equal
import pandas as pd

#4.12.1. assert_frame equal: Test Whether Two DataFrames are Similar
print ("---- assert_frame_equal ---- ")
df1 = pd.DataFrame({"coll": [1, 3, 42], "col2": [42, 5, 6]})
df2 = pd.DataFrame({"coll": [1, 3, 42], "col2": [42, 5, 6]})
print ( assert_frame_equal(df1, df2) )
#DataFrame.iloc[:, 0] (column name="coll") values are different (33.33333 %)

print ("---- assert_frame_equal check_like ---- ")
#If you want to ignore the order of index & columns when comparing two DataFrames ,
df1 = pd.DataFrame({"coll": [1, 2, 3], "col2": [4, 5, 6]})
df2 = pd.DataFrame({"col2": [4, 5, 6], "coll": [1, 2, 3]})
print ( assert_frame_equal(df1, df2, check_like=True) ) 

print ("---- compare ---- ")
#4.12.3. Compare the Difference Between Two DataFrames
df1 = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
df2 = pd.DataFrame({"col1": [1, 3, 42], "col2": [4, 5, 6]})
print ( df1.compare(df2) )