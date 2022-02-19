class Conto :
    def __init__(self,nome,conto):
        self.nome=nome
        self.conto=conto
    def descrizione(self):
        print("Conto",self.nome,self.conto)

class ContoCorrente (Conto) :
    def __init__(self,nome,conto,importo):
        super().__init__(nome,conto)
        self.__saldo=importo
    def preleva(self,importo):
        if self.__saldo>=importo:
            self.__saldo -= importo;
            return self.__saldo;
        else:
            return 0
    def deposita(self,importo):
        self.__saldo += importo
    def descrizione(self):
        print("Conto corrente ", self.nome,self.conto,self.__saldo)

class Gestore:
    @staticmethod
    def bonifico(sorgente,destinazione,importo):
       sorgente.preleva(importo)
       destinazione.deposita(importo)
       print("Bonifico da ",sorgente.nome," a ",destinazione.nome," di importo ",importo)

c1 = ContoCorrente("Alberto",1,40000)
c2 = ContoCorrente("Valentina",2,3000)
c1.descrizione()
c2.descrizione()
Gestore.bonifico(c1,c2,200)
c1.descrizione()
c2.descrizione()
