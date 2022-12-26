#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter2/itertools.html#itertools-groupby-group-elements-in-an-iterable-by-a-key

from collections import Counter
from collections import namedtuple
from collections import defaultdict
from collections import ChainMap
from itertools import combinations
from itertools import starmap
from itertools import compress
from itertools import groupby
from itertools import zip_longest

## Counter
print("--- Counter for-loop ---")
#V1 FOR loop
char_list = ["a", "b", "c", "a", "d", "b", "b"]
print("From" ,char_list)
def custom_counter(list_: list):
    char_counter = {}
    for char in list_:
        if char not in char_counter:
            char_counter[char] = 1
        else:
            char_counter[char] += 1

    return char_counter
out=custom_counter(char_list)
print("to", out)
#V2 COUNTER LIB	
print("--- collections.Counter ---")
print("From" ,char_list)
out=Counter(char_list)
print("To", out)


## namedtuple
print("--- collections.namedtuple ---")
Person = namedtuple("Person", "name gender age")
print("From",Person)
alnao = Person("Alberto", "male","38")
love = Person("Liubov", "female","22")
print("To", alnao)
print("To",love.name,"age is",love.age)


#defaultdict
print("--- collections.defaultdict ---")
classes = defaultdict(lambda: "Outside")
classes["Math"] = "B23"
classes["Physics"] = "D24"
print(classes["Math"])
print(classes["Spanish"])


#ChainMap
print("--- collections.ChainMap ---")
fruits = {'apple': 2, 'tomato': 1}
veggies = {'carrot': 3, 'tomato': 1}
food = ChainMap(fruits, veggies) 
print(food)
print( list(food.keys()) )


#Itertools A Better Way to Iterate Through a Pair of Values in a Python List
print("--- Itertools combinations ---")
num_list = [1, 2, 42]
comb = combinations(num_list, 2)  # use this
for pair in list(comb):
    print(pair)


#starmap Apply a Function With More Than 2 Arguments to Elements in a List
print("--- Itertools starmap ---")
nums = [(1, 2), (21, 2), (2, 5)]
def multiply_starmap(x: float, y: float):
    return x * y
out=list(starmap(multiply_starmap, nums))
print(out)


# compress Filter a List Using Booleans
print("--- Itertools compress ---")
fruits = ["apple", "orange", "banana", "grape", "lemon"]
chosen = [1, 0, 0, 1, 1]
out=list(compress(fruits, chosen))
print(out)


#groupby Group Elements in an Iterable by a Key
print("--- Itertools groupby ---")
prices = [("apple", 3), ("orange", 2), ("apple", 4), ("orange", 1), ("grape", 3)]
key_func = lambda x: x[0]
# Sort the elements in the list by the key
prices.sort(key=key_func)
# Group elements in the list by the key
for key, group in groupby(prices, key_func):
    print(key, ":", list(group))


#ZIP allows you to aggregate elements from each of the iterables. However, zip doesn’t show all pairs of elements when iterables have different lengths.
print("--- ZIP generic ---")
fruits = ["apple", "orange", "grape"]
prices = [1, 2]
out=list(zip(fruits, prices))
print(out)
print("--- itertools generic ---")
out=list(zip_longest(fruits, prices, fillvalue="-"))
print(out)


print("--- END --- ")