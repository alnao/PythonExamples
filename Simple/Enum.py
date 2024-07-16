from enum import Enum
class ColorePrimario(Enum):
    ROSSO=1
    VERDE=2
    BLU=3
class PuntoCardinale(Enum):
    NORD='N'
    SUD='S'
    OVEST='O'
    EST='E'
    SUD2='S' #DUE MEMBRI CON LO STESSO VALORE SONO VISTI COME LO STESSO

for direzione in PuntoCardinale:
    print(f"Nome: {direzione.name}, Valore: {direzione.value}")

print(PuntoCardinale.SUD == PuntoCardinale.NORD) #FLASE
print(PuntoCardinale.SUD == PuntoCardinale.SUD)
print(PuntoCardinale.SUD == PuntoCardinale.SUD2) 
print(PuntoCardinale.SUD is PuntoCardinale.NORD) #FALSE
print(PuntoCardinale.SUD is PuntoCardinale.SUD2) #TRUE #DUE MEMBRI CON LO STESSO VALORE SONO VISTI COME LO STESSO

print(PuntoCardinale.SUD == 'S' ) #FALSE
print(PuntoCardinale.SUD.value == 'S' ) #TRUE

print ("---------- Stagioni metodi nelle classi")
class Stagioni(Enum):
    PRIMAVERA=1
    ESTATE=2
    AUTUNNO=3
    INVERNO=4
    def descrizione(self):
        return {
            Stagioni.PRIMAVERA: "Bello",
            Stagioni.ESTATE: "Caldo",
            Stagioni.AUTUNNO: "Nebbia",
            Stagioni.INVERNO: "Freddo",
        }[self] #necessario mettere self tra quadre
    @property #definizione di una proprieta
    def fa_caldo(self):
        return self in {Stagioni.PRIMAVERA,Stagioni.ESTATE}

stagione_corrente=Stagioni.ESTATE
print ( stagione_corrente.descrizione() )
print ( stagione_corrente.fa_caldo )
print ("----------")