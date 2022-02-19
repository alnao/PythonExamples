class ContoCorrente:
    def __init__(self,nome,conto,importo):
        self.nome=nome
        self.conto=conto
        self.saldo=importo
    def preleva(self,importo):
        if self.saldo>=importo:
            self.saldo -= importo;
            return self.saldo;
        else:
            return 0
    def deposita(self,importo):
        self.saldo += importo
    def descrizione(self):
        print("Conto corrente ", self.nome,self.conto,self.saldo)

c1 = ContoCorrente("Alberto",1,40000)
c2 = ContoCorrente("Valentina",2,2000)
c1.descrizione()
c2.descrizione()
c1.preleva(200)
c2.deposita(200)
c1.descrizione()
c2.descrizione()
 
# :-(
# print(c1.saldo)