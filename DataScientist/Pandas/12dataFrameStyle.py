#ßee https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter3/style_dataframe.html
# pip install jinja2
# pip install display
# pip install ipython
#documentation see https://pandas.pydata.org/pandas-docs/stable/user_guide/style.html
#
#note: in terminal/console DOESN'T WORK
#
import pandas as pd 
from IPython.display import display

df = pd.DataFrame({"col1": [-5, -2, 1, 4], "col2": [2, 3, -1, 4]})
df.style.background_gradient()
def highlight_number(row):
    return [
        "background-color: red; color: white"
        if cell <= 0
        else "background-color: green; color: white"
        for cell in row
    ]
def color_negative_red(val):

    color = 'blue' if val > 90 else 'black'
    return 'color: % s' % color
display ( df.style.apply(highlight_number) )
#df.style.applymap(color_negative_red)


#see https://www.geeksforgeeks.org/display-the-pandas-dataframe-in-table-style/
#ßee https://towardsdatascience.com/style-pandas-dataframe-like-a-master-6b02bf6468b0?gi=e21c928e4ef1