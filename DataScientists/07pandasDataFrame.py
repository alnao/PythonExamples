#07pandasDataFrame
#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/change_values.html
#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/get_values.html#

import pandas as pd 
import numpy as np #np.nan

#- DataFrame {"a": [1, 2, 3], "b": [4, 5, 6]}
print ("---- DataFrame base ---- ")
df = pd.DataFrame({"a": [1, 2, 3], "b": [5, 6, 8]})
print (df)

#- assign e pipe
print ("---- Assign e pipe ---- ")
def get_diff(df):
    return df.assign(diff=df.b - df.a)
df = df.pipe(get_diff)
print (df)

#- apply If you want to apply only one function to a column of a DataFrame
print ("---- Apply ---- ")
df["diffDouble"] = df["diff"].apply(lambda row: row * 2)
print (df)

#Applymap apply a function to a DataFrame elementwise
print ("---- ApplyMap ---- ")
dfAM= df.applymap(lambda val: 'failed' if val < 5 else 'passed')
print (dfAM)

#Assign multiple  you can do everything in one line of code with df.assign.
print ("---- Assign multiple ---- ")
df = df.assign(c=lambda x: x.a * 42 + x.b).assign(
    d=lambda x: x.b * x.c
)
print (df)


#.explode
print ("---- .explode ---- ")
df = pd.DataFrame({"a": [[1, 2], [4, 5]], "b": [11, 13]})
print (df)
df=df.explode("a")
print (df)

#Split 
print ("---- .split ---- ")
df = pd.DataFrame({"a": ["6,7", "8,9"], "b": [11, 13]})
df.a = df.a.str.split(",")
df = df.explode("a")
print (df)

#fillna Fill the Current Missing Value 
print ("---- .fillna ---- ")
df = pd.DataFrame({"a": [1, np.nan, 3, 3], "b": [4, 5, 4, np.nan]})
df1 = df.fillna(42) #costant
print (df1)
df2 = df.fillna(method="ffill") #If you want to use the previous value in a column
print (df2)
df3 = df.fillna(df.mode().iloc[0]) #most frequent categories in a column,
print (df3)




#pandas.Series.pct_change: Find The Percentage Change Between The Current and a Prior Element in a pandas Series
print ("---- pct_change Percentage Change---- ")
df = pd.DataFrame({"a": [20, 35, 10], "b": [1, 2, 3]})
print ( df.a.pct_change() )

#Calculate the Difference Between Rows of a pandas DataFrame
print ("---- DataFrame.diff ---- ")
diff = df.diff() # diff2 = df.diff(periods=2)
print ( diff )

#shift . You can shift the rows up to match the first difference with the first index
print ("---- DataFrame.shift ---- ")
shift = diff.shift(-1)
print ( shift )

#dropna This will leave the first index null.
print ("---- DataFrame.dropna ---- ")
processed_df = shift.dropna()
print ( processed_df )


#df.to_dict: Turn a DataFrame into a Dictionary
print ("---- DataFrame into Dictionary ---- ")
df = pd.DataFrame({"fruits": ["apple", "orange", "grape"], "price": [1, 2, 3]})
print(df)
d= df.to_dict()
print (d)
#Records
print ("---- DataFrame into Dictionary and records ---- ")
d2=df.to_dict(orient="records")
print (d2)

# DataFrame.cumsum: Get Cumulative Sum Over Each Column
print ("---- DataFrame cumsum ---- ")
df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 33]})
df = df.cumsum()
print(df)

#Get the Sum of All Columns in a pandas DataFrame
print ("---- DataFrame Sum ---- ")
df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 33]})
df = df.sum(axis=1) 
print(df)

