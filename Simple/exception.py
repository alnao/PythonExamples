
#exception
def myFunc(a,b):
    try:
        val=a // b
    except ZeroDivisionError as target:
        val=0
        print (target.args)
        #raise #raise to re-run exception
    else:
        print(val)
    finally:
        return val

myFunc(10,2)
myFunc(10,0)  # ZeroDivisionError: integer division or modulo by zero

#raise example
#for i in range(50):
#	print(i)
#	raise IndexError("NOOOOO, first element")

#assert
#x=10
#assert x==5 , "different value"