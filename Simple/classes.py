#see https://www.youtube.com/watch?v=9SQTYoQkeoM
#see https://www.geeksforgeeks.org/python-functools-total_ordering/
from functools import total_ordering 

@total_ordering
class Persona:
    def __init__(self, nome :str , age : int):
        self.nome=nome
        self.age=age
    def work(self):
        print(f'{self.name} is working ... ')
    def sleep(self):
        print(f'{self.name} is sleeping ... but dreaming about working')
    #compare
    def __eq__(self, other) -> bool:
        return self.__dict__ == other.__dict__
    def __lt__(self, other) -> bool:
        return (self.nome.lower(),self.age) < (other.nome.lower(),other.age)
    #tostring 
    def __str__(self):
        return f'{self.nome} {self.age}'
    def __repr__(self):
        return self.__str__()
    #special method call https://www.geeksforgeeks.org/__call__-in-python/?ref=ml_lbp  
    def __call__(self): 
        print("Instance is called via special method") 
  
def main():
    #compare object
    alberto = Persona("Alberto",24)
    alnao = Persona("Alberto",24)
    print ( "Alberto e alnao sono  uguali?" , alberto == alnao )
    andrea = Persona("Andrea",33)
    print ( "Alberto minore di andrea?" , alberto < andrea )
    pietro = Persona("Pietro",64)
    #sort with key-method
    lista=[pietro,alberto,andrea]
    def get_age(persona): 
        return persona.age
    lista_ordinata=sorted(lista, reverse = True, key=get_age)
    print ( "Lista ordinata per età decredente:", lista_ordinata )

if __name__ == '__main__':
    main()