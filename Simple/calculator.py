import math
from typing import Union
import unittest

"""
Classe Calculator e classe TestCalculator per testare la calculator
presenza del main per avviare i test con l'istruzione unittest.main()
oppure lanciare il comando
    $ python -m unittest calculator.py
"""

class Calculator:
    """Una classe per eseguire calcoli matematici di base e avanzati."""
    
    @staticmethod
    def add(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
        return x + y
    
    @staticmethod
    def subtract(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
        return x - y
    
    @staticmethod
    def multiply(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
        return x * y
    
    @staticmethod
    def divide(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
        if y == 0:
            raise ValueError("Impossibile dividere per zero")
        return x / y
    
    @staticmethod
    def power(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
        return math.pow(x, y)
    
    @staticmethod
    def square_root(x: Union[int, float]) -> Union[int, float]:
        if x < 0:
            raise ValueError("Impossibile calcolare la radice quadrata di un numero negativo")
        return math.sqrt(x)

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()
    
    def test_add(self):
        self.assertEqual(self.calc.add(3, 5), 8)
        self.assertEqual(self.calc.add(-1, 1), 0)
        self.assertEqual(self.calc.add(40, 2), 42)
    
    def test_subtract(self):
        self.assertEqual(self.calc.subtract(5, 3), 2)
        self.assertEqual(self.calc.subtract(1, 1), 0)
        self.assertEqual(self.calc.subtract(-1, -1), 0)
    
    def test_multiply(self):
        self.assertEqual(self.calc.multiply(3, 5), 15)
        self.assertEqual(self.calc.multiply(-2, 3), -6)
        self.assertEqual(self.calc.multiply(0, 5), 0)
    
    def test_divide(self):
        self.assertEqual(self.calc.divide(6, 2), 3)
        self.assertEqual(self.calc.divide(5, 2), 2.5)
        with self.assertRaises(ValueError):
            self.calc.divide(5, 0)
    
    def test_power(self):
        self.assertEqual(self.calc.power(2, 3), 8)
        self.assertEqual(self.calc.power(5, 0), 1)
        self.assertEqual(self.calc.power(2, -1), 0.5)
    
    def test_square_root(self):
        self.assertEqual(self.calc.square_root(4), 2)
        self.assertEqual(self.calc.square_root(0), 0)
        with self.assertRaises(ValueError):
            self.calc.square_root(-1)

if __name__ == '__main__':
    unittest.main()