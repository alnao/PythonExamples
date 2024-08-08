#pip install sympy
from sympy import *

#Rational (frac)
frac = Rational(25, 15)
print(frac)
frac = frac +1
print(frac)

#Symbols
x, y = symbols("x y")
expr = 3 * x + y
print ( expr +2 ) 

#expand e factor
expr = x * (3 * x + y)
expansion = expand(expr)
print (expansion)
factor(expansion)
print (expansion)
 
# Solve an Equation e subs
eq = (2 * x + 1) * 3 * x
sol= solve(eq, x)
print (sol)
sol = eq.subs(x, 2)
print (sol)

#Derivatives, Integrals, and Limit
expr = 1 / (x ** 2) # sin(x) ** 2 + 2 * x
res = diff(expr)
print ( res )
res = integrate(expr)
print ( res )
expr=1 / (x ** 2)
res = limit( expr , x, oo)
print ( res )
res = limit( expr , x, 2)
print ( res )

#Special = factorial(x) e rewrite
print (factorial(x)) 
print ( tan(x).rewrite(cos) )


#print latex
print(latex( res ))