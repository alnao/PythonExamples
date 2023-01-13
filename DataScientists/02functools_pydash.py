from functools import partial
from functools import reduce
from pydash import py_

#Functools
def linear_func(x, a, b):
    return a * x + b
linear_func_partial = partial(linear_func, a=2, b=3)
print(linear_func_partial(2))
print(linear_func_partial(4))


#functools.singledispatch
data = {"a": [1, 2, 3], "b": [4, 5, 6]}
data2 = [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}]
from functools import singledispatch
@singledispatch
def process_data2(data):
    raise NotImplementedError("Please implement process_data2")
@process_data2.register
def process_dict2(data: dict):
    print("Dict is processed")
@process_data2.register
def process_list2(data: list):
    print("List is processed")
process_data2(data)
process_data2(data2)


#functools.reduce
def add_nums(num1, num2):
    res = num1 + num2
    print(f"{num1} + {num2} = {res}")
    return res
print(reduce(add_nums, [1, 2, 3], 2))


# pydash.flatten: Flatten a Nested Python List
a = [[1, 2], [3, 4, 5]]
a= py_.flatten(a) 
print ( a )


# pydash.flatten_deep: Flatten a Deeply Nested Python List
b = [[1, 2, [4, 5,99]], [6, 7]]
b= py_.flatten_deep(b)
print( b )


#pydash.chunk: Split Elements into Groups
a = [1, 2, 3, 4, 5]
a= py_.chunk(a, 2)
print ( a )


#Omit Dictionary’s Attribute
fruits = {"name": "apple", "color": "red", "taste": "sweet"}
ff = py_.omit(fruits, "name")
print (ff )


#Get Nested Dictionary’s Attribute
apple = {
    "price": {
        "in_season": {"store": {"Walmart": [2, 4], "Aldi": 1}},
        "out_of_season": {"store": {"Walmart": [3, 5], "Aldi": 2}},
    }
}
print ( apple["price"]["in_season"]["store"]["Walmart"][1] )
print ( py_.get(apple, "price.in_season.store.Walmart")[1] )


#Find Item Index Using a Function
fruits = [
    {"name": "apple", "price": 2},
    {"name": "orange", "price": 2},
    {"name": "grapes", "price": 4},
]
i=fruits.index({"name": "apple", "price": 2})
print ( i )


#3.4.3.2. Find Objects With Matching Style
fruits = [
    {"name": "apple", "price": 2},
    {"name": "orange", "price": 2},
    {"name": "grapes", "price": 4},
]
p = py_.filter_(fruits, {"name": "apple"})
print ( p )


#Get Nested Object Value
l = [
    {"apple": {"price": [0, 1], "color": "red"}},
    {"apple": {"price": [2, 3], "color": "green"}},
]
l = py_.map_(l, "apple.price[1]")
print (l)


#3.4.4.1. Execute a Function n Times
r=py_.times(4, lambda: "I have just bought some apple")
print ( r  )
