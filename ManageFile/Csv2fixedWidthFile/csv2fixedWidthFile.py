import json
import csv
import codecs
import os

def aggiungiCampoARiga(row,campo):
    tipo=campo["tipo"]
    valore=campo["valore"]
    lunghezza=int(campo["lunghezza"])
    if tipo=='val':
        return padString ( valore ,lunghezza )
    valore=row[valore] #recupero la colonna valore dal tracciato.csv nel input.csv
    if tipo=='str':
        return padString ( valore ,lunghezza )
    if tipo=='int':
        return padInt ( valore ,lunghezza )
    if tipo=='dateIta2YYYYMMDD':
        return padDateIta2YYYYMMDD ( valore ,lunghezza )
    raise IndexError("Errore: tipo non rinosciuto " + tipo)

def padString(valore : str,lunghezza : int,v=" "):
    return valore.ljust(lunghezza,v)

def padInt(valore : str,lunghezza : int,v="0"):
    return valore.rjust(lunghezza,v)

def padDateIta2YYYYMMDD(valore,lunghezza,v="0"):
    return valore  #TODO

#metodo che prende un csv e ritorna una lista di dict
def loadCsvInList(dataFile):
    reader= csv.reader(dataFile, delimiter=';')
    lista=[]
    intestazioneInput=next(reader, None)  # skip the headers in intestazioneInput #print("Riga: " + json.dumps(intestazioneInput) )
    for row in reader:
        riga={}
        #ciclo per ogni colonna
        for col_nr in range(0,len(intestazioneInput)-1):
            try:
                riga[intestazioneInput[col_nr]]=row[col_nr]
            except:
                riga[intestazioneInput[col_nr]]=""
        lista.append(riga)
    return lista

#csv2fixedWithFile
def csv2fixedWithFile(dataFileInput, dataFileTracciato):
    fileOutput=""
    #per ogni riga del dataFileTracciato creo una lista con l'elenco dei campi
    listaCampi=loadCsvInList(dataFileInput) # campi arrivano campo0;val;5;03365;abi
    dati=loadCsvInList(dataFileTracciato) #print("Riga: " + json.dumps(dati) )     
    for row in dati: #for row in csv.DictReader(codecs.getreader('utf-8')(dataFileInput), delimiter=';'):
        stringaRiga=""
        #per ogni campo lo aggiungo prendendolo
        for campo in listaCampi:
            stringaRiga+=aggiungiCampoARiga(row,campo)
        fileOutput+=stringaRiga+"\n"
    return fileOutput

print(__name__)

with open("tracciato.csv","rt") as dataFileInput:
    with open("input.csv","rt") as dataFileTracciato:
        output=csv2fixedWithFile( dataFileInput.readlines() , dataFileTracciato.readlines() ) 
print(output)
with open('OUT.txt', 'w') as the_file:
  the_file.write(output)