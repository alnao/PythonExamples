import numpy as np
import array_to_latex as a2l #pip install array-to-latex
#import matplotlib.pyplot as plt
#ßee https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter4/Numpy.html

#Flatten a NumPy Array
print ("---- Flatten a NumPy Array : ravel---- ")
arr = np.array([[1, 2], [3, 4]])
print ( arr ) 
r = np.ravel(arr)
print ( r ) 
r = np.ravel(arr, order="F")
print ( r ) 

print ("---- np.squeeze Remove Axes of Length One From an Array---- ")
arr = np.array([[[1], [2]], [[3], [4]]])
print ( arr )
r = arr.shape 
print ( r )
r = np.squeeze(arr)
print ( r )

print ("---- NumPy.take: Take Elements From an Array ---- ")
arr = [3, 4, 1, 4, 5]
indices = [1, 3, 4]
print ( arr )
r = np.take(arr, indices)
print ( r )

print ("---- Use List to Change the Positions of Rows or Columns in a NumPy Array ---- ")
arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
print ( arr )
new_row_position = [1, 2, 0]
r = arr[new_row_position, :]
print ( r )

print ("--- Difference Between NumPy’s All and Any Methods --- ")
a = np.array([[1, 2, 1], [2, 2, 5]])
mask_all = (a < 3).all(axis=1)
r = a[mask_all]
print ( r )

print ("--- Double numpy.argsort: Get Rank of Values in an Array ---")
a = np.array([2, 1, 4, 7, 3])
r = a.argsort().argsort()
print ( r )

print ("--- Get the Index of the Max Value in a NumPy Array ---")
a = np.array([0.2, 0.4, 0.7, 0.3])
r = np.argmax(a)
print ( r )

print ("--- np.where: Replace Elements of a NumPy Array Based on a Condition ---")
arr = np.array([[1, 4, 10, 15], [2, 3, 8, 9]])
r = np.where(arr < 5, arr * 2, arr)
print ( r )

print ("--- array-to-latex: Turn a NumPy Array into Latex ----") #pip install array-to-latex
a = np.array([[1, 2, 3], [4, 5, 6]])
latex = a2l.to_ltx(a)
print ( latex )

print ("--- NumPy Comparison Operators ---")
a = np.array([1, 2, 3])
b = np.array([4, 1, 2])
print ( a < b )

#import matplotlib.pyplot as plt
#print ("--- NumPy.linspace: Get Evenly Spaced Numbers Over a Specific Interval ---")
#x = np.linspace(2, 4, num=10)
#print ( x )
#y = np.arange(10)
#plt.plot(x, y)
#plt.show()
