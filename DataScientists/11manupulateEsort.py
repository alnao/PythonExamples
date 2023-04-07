#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/data_types.html

import pandas as pd 

print ("---- select_dtypes ---- ")
#select_dtypes: Return a Subset of a DataFrame Including/Excluding Columns Based on Their dtype
df = pd.DataFrame({"col1": ["a", "b", "c"], "col2": [1, 2, 3], "col3": [0.1, 0.2, 0.3]})
print ( df.select_dtypes(include=["int64", "float64"]) )

print ("---- sort_values ---- ")
#pandas.Categorical: Turn a List of Strings into a Categorical Variable
size = pd.Categorical(['M', 'S', 'M', 'L'], ordered=True, categories=['S', 'M', 'L'])
df = pd.DataFrame({'size': size, 'val': [5, 4, 3, 6]})
print ( df.sort_values(by='size') )
       
#Sort Rows or Columns of a DataFrame)
print ("---- sort_values ---- ")
df = pd.DataFrame(
    {"col1": ["large", "small", "mini", "medium", "mini"], "col2": [1, 2, 3, 4, 5]}
)
ordered_sizes = "large", "medium", "small", "mini"
df.col1 = df.col1.astype("category")
df.col1.cat.set_categories(ordered_sizes, ordered=True, inplace=True)
print ( df.sort_values(by="col1") )


print ("---- Manipulate Text Data ---- ")
#4.10.1. pandas.Series.str: Manipulate Text Data in a Pandas Series
fruits = pd.Series(['Orange', 'Apple', 'Grape'])
print ( fruits.str.lower().str.replace("e", "a") )

print ("---- startswith ---- ")
#4.10.2. DataFrame.columns.str.startswith: Find DataFrame’s Columns that Start With a Pattern
df = pd.DataFrame({'pricel': [1, 2, 3],
                    'aaaa': [2, 3, 4],
                    'year': [2020, 2021, 2021]})
mask = df.columns.str.startswith('price')
print ( df.loc[:, mask] )

print ("---- contains ---- ")
#4.10.3. Find Rows Containing One of the Substrings in a List
s = pd.Series(['bunny', 'monkey', 'funny', 'flower'])
sub_str = ['ny', 'ey']
join_str = '|'.join(sub_str)
print ( s[s.str.contains(join_str)] )

