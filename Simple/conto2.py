class ContoCorrente:
    def __init__(self,nome,conto,importo):
        self.nome=nome
        self.conto=conto
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
    @property
    def saldo(self):
        return self.__saldo
    @saldo.setter
    def saldo(self, importo):
        self.preleva(self.__saldo) #scarico tutto il saldo
        self.deposita(importo) #deposito il saldo


c1 = ContoCorrente("Alberto",1,40000)
c1.descrizione()
c1.preleva(200)
c1.descrizione()

# non funziona
# print(c1.__saldo)

# funziona perchè properties def saldo(self)
print(c1.saldo)
# funziona perchè definita @saldo.setter
c1.saldo=1000
print(c1.saldo)