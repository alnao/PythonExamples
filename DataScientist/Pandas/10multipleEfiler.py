#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/combine_dataframes.html
#ßee https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/filter.html
import pandas as pd 
import numpy as np
#from collections import Counter

print ("---- combine_first ---- ")
#4.6.1. pandas.DataFrame.combine_first: Update Null Elements Using Another DataFrame
df1 = pd.DataFrame({"orange": [None, 5], "apple": [None, 1]})
df2 = pd.DataFrame({"orange": [1, 3], "apple": [42, 2]})
print(df1.combine_first(df2))


print ("---- Merge ---- ")
#4.6.2. df.merge: Merge DataFrame Based on Columns
df1 = pd.DataFrame({"key1": ["a", "a", "b", "b", "a"], "value": [1, 2, 3, 4, 5]})
df2 = pd.DataFrame({"key2": ["a", "b", "c"], "value": [6, 7, 8]})
print ( df1.merge(df2, left_on="key1", right_on="key2") )


print ("---- Merge Suffixes ---- ")
#4.6.3. Specify Suffixes When Using df.merge()
df1 = pd.DataFrame({"left_key": [1, 2, 3], "a": [4, 42, 6]})
df2 = pd.DataFrame({"right_key": [1, 3, 2], "a": [5, 6, 42]})
print ( df1.merge(df2, left_on="left_key", right_on="right_key") )

print ("---- insert ---- ")
#4.6.4. DataFrame.insert: Insert a Column Into a DataFrame at a Specified Location
df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
df.insert(loc=1, column='c', value=[42, 33]) 
print ( df )

#https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/filter.html
#4.7.1. Pandas.Series.isin: Filter Rows Only If Column Contains Values From Another List
print ("---- isin ---- ")
df = pd.DataFrame({'col_a': [1, 2, 3], 'b': [4, 5, 6]})
l = [1, 2, 6, 7]
print ( df.col_a.isin(l) )
df = df[df.col_a.isin(l)]
print (df)

#4.7.2. df.query: Query Columns Using Boolean Expression
print ("---- Query boolean ---- ")
df = pd.DataFrame(
    {"fruit": ["apple", "orange", "grape", "grape"], "price": [4, 5, 6, 42]}
)
print(df[(df.price > 4) & (df.fruit == "grape")])
print ( df.query("price > 4 & fruit == 'grape'") )


#4.7.3. transform: Filter a pandas DataFrame by Value Counts
print ("---- groupby count ---- ")
df = pd.DataFrame({"type": ["A", "A", "O", "B", "O", "A"], "value": [5, 3, 2, 1, 4, 42]})
dfg=df.groupby("type")["type"].count()
print( dfg )
#print ( df.loc[df.groupby("type")["type"].count() > 1] )
#€xample?
print ( df.loc[df.groupby("type")["type"].transform("size") > 1] )


#4.7.4. df.filter: Filter Columns Based on a Subset of Their Names
print ("---- Filter Columns ---- ")
df = pd.DataFrame({"cat1": ["a", "b"], "cat2": ["b", "c"], "num1": [1, 42]})
print ( df.filter(like='cat', axis=1) )


#4.7.5. Filter a pandas DataFrame Based on Index’s Name
print ("---- Filter Index’s Name ---- ")
values = np.array([[1, 2], [3, 4], [5, 6]])
df = pd.DataFrame(
    values, 
    index=["user1", "user2", "user3"], 
    columns=["col1", "col2"]
)
print ( df.filter(items=['user1', 'user3'], axis=0) )
print ( df.loc[['user1', 'user3'], :] )


#4.7.6. all: Select Rows with All NaN Values
print ("---- Filter NaN Values ---- ")
df = pd.DataFrame({'a': [1, 42, float('nan')], 'b': [1, float('nan'), float('nan')]})
is_all_nan = df.isna().all(axis=1)
print ( is_all_nan  )


#4.7.7. pandas.clip: Exclude Outliers
#If you want to trim values that the outliers, one of the methods is to use df.clip.
#Below is how to use the 0.5-quantile as the lower threshold and .95-quantile as the upper threshold
print ("---- pandas.clip ---- ")
data = {"col0": [9, -3, 0, -1, 5]}
df = pd.DataFrame(data)
lower = df.col0.quantile(0.05)
upper = df.col0.quantile(0.95)
print ( df.clip(lower=lower, upper=upper) )
