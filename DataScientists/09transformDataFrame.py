import pandas as pd 
#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/transform_dataframe.html
from collections import Counter

#DF df2 = df.agg(["sum", count_two])
#4.4.1. pandas.DataFrame.agg: Aggregate over Columns or Rows Using Multiple Operations
print ("---- agg ---- ")
def count_two(nums: list):
    return Counter(nums)[2]
df = pd.DataFrame({"coll": [1, 3, 5], "col2": [2, 4, 6]})
df2 = df.agg(["sum", count_two])
print ( df2 )

#4.4.2. pandas.DataFrame.agg: Apply Different Aggregations to Different Columns
print ("---- agg 2---- ")
df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 3, 4, 5]})
df2 = df.agg({"a": ["sum", "mean"], "b": ["min", "max"]})
print ( df2 )

#4.4.3. Group DataFrame’s Rows into a List Using groupby
print ("---- groupby ---- ")
df = pd.DataFrame(
    {
        "col1": [1, 2, 3, 4, 3],
        "col2": ["a", "a", "b", "b", "c"],
        "col3": ["d", "e", "f", "g", "h"],
    }
)
df2 = df.groupby(["col2"]).agg({"col1": "mean", "col3": lambda x: list(x)})
print ( df2 )

#4.4.4. Get the N Largest Values for Each Category in a DataFrame
print ("---- groupby2 ---- ")
df = pd.DataFrame({"type": ["a", "a", "a", "b", "b"], "value": [1, 2, 3, 1, 2]})
# Get n largest values for each type
df2 = df.groupby("type").apply(lambda df_: df_.nlargest(2, "value")).reset_index(drop=True)
print ( df2 )

#4.4.5. Assign Name to a Pandas Aggregation
print ("---- groupby3 ---- ")
df = pd.DataFrame({"size": ["S", "S", "M", "L"], "price": [2, 3, 4, 5]})
df2 = df.groupby('size').agg({'price': 'mean'})
print ( df2 )
df3 = df.groupby('size').agg(mean_price=('price', 'mean'))
print ( df3 )

#4.4.6. pandas.pivot_table: Turn Your DataFrame Into a Pivot Table
print ("---- pivot_table ---- ")
df = pd.DataFrame(
    {
        "item": ["apple", "apple", "apple", "apple", "apple"],
        "size": ["small", "small", "large", "large", "large"],
        "location": ["Walmart", "Aldi", "Walmart", "Aldi", "Aldi"],
        "price": [3, 2, 4, 3, 2.5],
    }
)
df2 = pd.pivot_table(
    df, values="price", index=["item", "size"], columns=["location"], aggfunc="mean"
)
print ( df2 )

#4.4.7. DataFrame.groupby.sample: Get a Random Sample of Items from Each Category in a Column
print ("---- groupby4 ---- ")
df = pd.DataFrame({"col1": ["a", "a", "b", "c", "c", "d"], "col2": [4, 5, 6, 7, 8, 9]})
df2 = df.groupby("col1").sample(n=1)
print ( df2 )
#df3 = df.groupby("col1").sample(n=2)
#print ( df3 )

#4.4.8. size: Compute the Size of Each Group
print ("---- groupby5 ---- ")
df = pd.DataFrame(
    {"col1": ["a", "b", "b", "c", "c", "d"], "col2": ["S", "S", "M", "L", "L", "L"]}
)
df2 = df.groupby(['col1']).count()
print ( df2 )

#4.4.9. pandas.melt: Unpivot a DataFrame
print ("---- melt ---- ")
df = pd.DataFrame(
    {"fruit": ["apple", "orange"], "Aldi": [1, 2], "Walmart": [3, 4], "Costco": [5, 6]}
)
df2 = df.melt(id_vars=["fruit"], value_vars=["Aldi", "Walmart", "Costco"], var_name='store')
print ( df2 )


#4.4.10. pandas.crosstab: Create a Cross Tabulation
print ("---- crosstab ---- ")
network = [
    ("Ben", "Khuyen"),
    ("Ben", "Josh"),
    ("Lauren", "Thinh"),
    ("Lauren", "Khuyen"),
    ("Khuyen", "Josh"),
]
friends1 = pd.DataFrame(network, columns=["person1", "person2"])
friends2 = pd.DataFrame(network, columns=["person2", "person1"])
friends = pd.concat([friends1, friends2])
df2 = pd.crosstab(friends.person1, friends.person2)
print ( df2 )

#4.4.11. Turn a pandas Series into a pandas DataFrame
print ("---- get_dummies Series2DataFrame ---- ")
s = pd.Series(["a", "b", "a,b", "a,c"])
df2 = s.str.get_dummies(sep=",")
print ( df2 )
