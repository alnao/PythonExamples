#06pandasSeries
## see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/change_values.html
import pandas as pd 



#pandas.Series
print ("---- Series ---- ")
s = pd.Series(["a", "bb", "c", "bb"])
print (s)

#Series.map
print ("---- Series.map ---- ")
s=s.map({"a": 1, "bb": 42, "c": 3})
print (s)

#Series.map string
print ("---- Series.map string ---- ")
s = pd.Series(["berries", "apples", "cherries"])
s=s.map("Today I got some {} from my garden.".format)
print (s)


print ("----  Series ---- ")
s = pd.Series([5, 42, 44, 20], index=[20, 21, 22, 23])
print (s)
#You can access a group of rows by either using loc or iloc.
print ("---- DataFrame iloc e loc---- ")
print ( s.iloc[0] )
print ( s.iloc[2] )
# Get the value with the index of 20. 
print ( s.loc[20] )

#To get the values that are smaller than the upper bound and larger than the lower bound
print ("---- between 40 e 50---- ")
s2 = s[s.between(40, 50)]
print (s2)


#Turn a pandas Series into a NumPy Array
print ("---- Series into Array with values ---- ")
s = pd.Series(["apple", "orange", "grape"])
print (s.values)

#pandas.Series.cummax: Get the Cumulative Maximum
print ("---- Series cummax ---- ")
nums = pd.Series([4, 2, 5, 1, 6])
print ( nums.cummax() )

