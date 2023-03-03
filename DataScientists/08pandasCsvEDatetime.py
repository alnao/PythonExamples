import pandas as pd 
from pandas.tseries.offsets import DateOffset, BDay
#see https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
#see https://sparkbyexamples.com/pandas/pandas-read-csv-examples/
import warnings
warnings.filterwarnings("ignore")

pathFile="/mnt/Dati/Workspace/PythonExamples/DataScientists/08data.csv"
#read_csv with sep (or delimiter)
print ("---- .pd.read_csv ---- ")
df = pd.read_csv(pathFile, sep=";")
print ( df.info() )
print ( df )

#DF copy 
print ("---- copy ---- ")
df = pd.read_csv(pathFile, sep=";")
df3 = df.copy()
df3['col1'] = [1, 2, 3 ,4,5]
print (df)


#with index_col
print ("---- index_col ---- ")
df = pd.read_csv(pathFile, sep=";", index_col='name')
#print ( df.info() )
print ( df )

##with skiprows
print ("---- skiprows ---- ")
df = pd.read_csv(pathFile, sep=";", header=None, skiprows=2)
#print ( df.info() )
print ( df )

##with names columns
print ("---- skiprows ---- ")
columns = ['name','date1','date2','number']
df = pd.read_csv(pathFile, sep=";", names=columns )
print ( df )

##usecols=Load only Selected Columns
print ("---- usecols ---- ")
df = pd.read_csv ( pathFile, sep=";", usecols =['name','value']  )
print ( df )

## Timestamp e DateOffset
print ("---- Timestamp ---- ")
ts = pd.Timestamp('2021-10-10 9:00:00')
# Increase the timestamp by 3 months
ts = ts + DateOffset(months=3 ,years=1)
print ( ts )
## BDay business days
print ("---- BDay business days ---- ")
ts = ts + BDay(n=6)
print ( ts )

#rolling Find The Average of The Previous n Datapoints Using pandas
print ("---- rolling ---- ")
df = pd.read_csv(pathFile, sep=";")
df = df.rolling(3).mean()
print (df )

#pandas Grouper: Group Values Based on a Specific Frequency
print ("---- Grouper ---- ")
df = pd.read_csv(pathFile, sep=";")
df["date_column_1"] = pd.to_datetime(df["date_column_1"])
df = df.groupby(pd.Grouper(key="date_column_1", freq="1W")).mean()
print (df)

# subpart of date
print ("---- subpart of date ---- ")
df = pd.read_csv(pathFile, sep=";")
df["date_column_1"] = pd.to_datetime(df["date_column_1"])
df = df["date_column_1"].dt.year
#df["date"].dt.time
print (df)

# Get Rows within a Year Range
print ("---- Year Range ---- ")
df = pd.read_csv(pathFile, sep=";")
df = df.loc["2019":]
print (df)

#Select DataFrame Rows Before or After a Specific Date
print ("---- Before or After a Specific Date ---- ")
df = pd.read_csv(pathFile, sep=";")
filtered_df = df[df.date_column_1 > "2021-01-21"]
print (filtered_df)

#4.5.4. Read HTML Tables Using Pandas
#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/create_dataframe.html
print ("----  ---- ")
print ("---- Read HTML Tables Using Pandas ---- ")
df = pd.read_html('https://en.wikipedia.org/wiki/Poverty')
print (df[1] )

