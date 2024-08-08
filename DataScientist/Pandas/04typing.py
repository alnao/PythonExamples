#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter2/typing.html
from typing import Callable
from typing import Type 
from typing import Annotated
from typing import final 
from typing import Literal
from typing import Dict, Union



#If you want to specify an input is of type function, use typing.Callable.
def multiply(x: float, y: float) -> float:
    return x * y
def multiply_then_divide_by_two(multiply_func: Callable[[float, float], float], x: float, y: float) -> float:
    return multiply_func(x, y) / 2
res = multiply_then_divide_by_two(multiply, 4, 3)
print (res) # 6 = 4*3/2


#How do we use type hint to specify that fruit_type in make_fruit should be a subclass of Fruit?
#Use typing.Type instead.
class Fruit:
    def __init__(self, taste: str) -> None:
        self.taste = taste 
class Orange(Fruit):
    def orange():
        return "Orange"
class Apple(Fruit):
    def Apple():
        return "Apple"
def make_fruit(fruit_type: Type[Fruit], taste: str):
    return fruit_type(taste=taste)
orange = make_fruit(Orange, "sour")
print ( type( orange ) )
#print ( orange.taste )


#If you want to add metadata to your typehint such as units of measurement, use typing.Annotated.
def get_height_in_feet(height: Annotated[float, "meters"]):
    return height * 3.28084
print(get_height_in_feet(height=1))


#If you want to declare that some methods shouldn’t be overridden by subclasses, 
# #use the decorator typing.final.
class Dog:
    #@final 
    def bark(self) -> None:
        print("Woof")
class Dachshund(Dog):
    def bark(self) -> None:
        print("Ruff")
bim = Dachshund()
bim.bark()


#If you want to use type hints to check that a variable or a function 
# #parameter is in a set of literal values, use typing.Literal.
def get_price(fruit: Literal["apple", "orange"]):
    if fruit == "apple":
        return 1
    else:  # if it is orange
        return 2
print ( get_price("grape") )


#typing.Union[X, Y] is used to declare that a variable can be either X or Y. 
# In Python 3.10 and above, you can replace Union[X, Y] with X|Y.
# Before Python 3.10
def get_price1(grocery: Dict[str, Union[int, float]]):
    return grocery.values()
grocery = {"apple": 3, "orange": 2.5}
print (get_price1(grocery) )
#python 10
#def get_price2(grocery: dict[str, int | float]):
#    return grocery.values()
#grocery = {"apple": 3, "orange": 2.5}
#print ( get_price2(grocery) )