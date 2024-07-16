import math 

# piccoli esercizi, ogni classe ha il suo scopo e nel main i suoi messaggi di test

class Pianeta:
    def __init__(self,nome,risorse):
        self.nome = nome
        self.risorse =risorse
        self.successivo=None #serve per la prova linked list

class LinkedListPianeti:
    def __init__(self):
        self.testa=None
    def aggiungi_pianeta(self,nome_pianeta, risorse):
        nuovo_pianeta=Pianeta(nome_pianeta,risorse)
        if self.testa is None: #se è il primo
            self.testa=nuovo_pianeta
            return
        ultimo=self.testa 
        while ultimo.successivo: #se non è il primo , cerco l'ultimo
            ultimo=ultimo.successivo
        ultimo.successivo=nuovo_pianeta
    def visualizza_pianeti(self):
        current=self.testa
        while current:
            print(current.nome, end=" ->")
            current=current.successivo
        print("Fine viaggio")

class Astronave():
    def __init__(self,x,y,capacita_carico):
        self.x=x
        self.y=y
        self.capacita_carico=capacita_carico
        self.carico_attuale=0
        self.risorse_raccolte={}
    def muovi_a(self,dest_x,dest_y):
        self.x=dest_x
        self.y=dest_y
    def distanza_da(self,dest_x,dest_y):
        return math.sqrt( (dest_x-self.x)**2 + (dest_y-self.y)**2  )
    @staticmethod
    def messaggio_esplorazione(pianeta):
        return f"Stai esplorando il pianeta {pianeta}"
    @classmethod
    def astronave_standard(cls):
        return cls(x=0,y=0,capacita_carico=42)    
    def capacita_rimanente(self):
        return self.capacita_carico-self.carico_attuale
    def _puo_caricare(self,massa):
        return self.carico_attuale + massa <= self.capacita_carico
    def esplora(self,pianeta):
        print (Astronave.messaggio_esplorazione(pianeta.nome) )
        for risorsa,massa in pianeta.risorse.items():
            if self._puo_caricare(massa):
                self.carico_attuale+=massa
                self.risorse_raccolte[risorsa]=self.risorse_raccolte.get(risorsa,0)+massa
            else:
                print(f"Carico pieno, impossibile raccogliere la risorsa {risorsa}")

class ComputerCentrale:  #singleton così c'è solo
    _istanza=None 
    ##__init___ no perchè singleton
    def __new__(cls):
        if cls._istanza is None: #singleton così c'è solo una implementazione
            cls._istanza= super().__new__(cls)
            cls._istanza.stato="In attesa"
            cls._istanza.motori="Spenti"
        return cls._istanza
    def statoAstronave(self):
        return self._istanza.stato,self._istanza.motori
    def avviaMotori(self):
        self._istanza.stato="Movimento"
        self._istanza.motori="Accesi"
    def spegniMotori (self):
        self._istanza.stato="In attesa"
        self._istanza.motori="Spenti"

class Comunicazione:
    def __init__(self,mittente,messaggio):
        self.mittente =mittente
        self.messaggio =messaggio
    def __str__(self):
        return f"Da {self.mittente} : {self.messaggio}"
    
class StackComunicazioni: #lista comunicazioni LIFO
    def __init__(self,capacita=10):
        self.capacita =capacita
        self.comunicazioni = [] 
    def size(self):
        return len(self.comunicazioni)
    def push(self,comunicazione):
        if (self.size() < self.capacita):
            self.comunicazioni.append(comunicazione)
            return True
        else:
            print("Impossibile continuare perchè lista di comunicazioni piena")
            return False
    def pop(self):
        if (self.size() > 0):
            return self.comunicazioni.pop()
        else:
            return None
    def peek(self): #ultimo senza toglierlo
        if (self.size() > 0):
            return self.comunicazioni[-1] #ultimo senza toglierlo
        else:
            return None

def main():
    print("To boldly go where no man has gone before")
    #Parte1: muoversi per tot
    epsilon=Astronave(0,0,42)
    epsilon.muovi_a(42,33)
    distanza = epsilon.distanza_da(0,0)
    print (f"Distanza percorsa: {distanza}")

    print("--------------- Pianeti e risorse ")
    #Parte2: rifornimento
    terra=Pianeta("Terra",{"ferro":12,"oro":1})
    marte=Pianeta("Marte",{"ferro":7,"rame":10})
    giove=Pianeta("Giove",{"platino":7,"argento":12})
    voyager=Astronave.astronave_standard()
    voyager.esplora(terra)
    voyager.esplora(marte)
    voyager.esplora(giove)
    print ("Risorse nell'astronave:")
    for risorsa,massa in voyager.risorse_raccolte.items():
        print(f"{risorsa}\t{massa}")        
    print("--------------- Test singleton, cioè due oggetti ma classe unica con new al posto di init")
    c1=ComputerCentrale()
    c2=ComputerCentrale()
    print ("Sono lo stesso oggetto con singleton?",c1==c2)
    print ("C1=", c1.statoAstronave() )
    c1.avviaMotori()
    print ("C2=", c2.statoAstronave() )
    c2.spegniMotori()
    print ("C1=", c1.statoAstronave() )

    print("--------------- LinkedListPianeti lista pianeti: ")
    lista_pianeti=LinkedListPianeti()
    lista_pianeti.aggiungi_pianeta("Terra",{"ferro":12,"oro":1})
    lista_pianeti.aggiungi_pianeta("Marte",{"ferro":7,"rame":10})
    lista_pianeti.aggiungi_pianeta("Giove",{"platino":7,"argento":12})
    lista_pianeti.visualizza_pianeti()

    print("--------------- Stack messaggi : ")
    stack_comunicazioni = StackComunicazioni(3)
    c1=Comunicazione("Alberto","Ciao")
    c2=Comunicazione("Valentina","Ciao, come stai?")
    c3=Comunicazione("Alberto","io tutto bene, te?")
    c4=Comunicazione("Valentina","anche io tutto bene")
    stack_comunicazioni.push(c1)
    stack_comunicazioni.push(c2)
    stack_comunicazioni.push(c3)
    stack_comunicazioni.push(c4) #KO
    print ( stack_comunicazioni.peek() )
    stack_comunicazioni.pop()
    stack_comunicazioni.push(c4) #OK
    print ( stack_comunicazioni.peek() )
    
if __name__ == '__main__':
    main()
