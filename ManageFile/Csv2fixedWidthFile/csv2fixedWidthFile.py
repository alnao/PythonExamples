import json
import csv
import codecs
import os

def aggiungiCampoARiga(intestazioneInput,row,campo):
    tipo=campo["tipo"]
    valore=campo["valore"]
    lunghezza=int(campo["lunghezza"])
    if tipo=='val':
        return padString ( valore ,lunghezza )
    indiceValore=100000000
    for col_nr in  range(0,len(intestazioneInput)-1):
        if intestazioneInput[col_nr]==valore: #se la colonna del file row è uguale al nome del campo 
            indiceValore=col_nr
    if tipo=='str':
        return padString ( row[indiceValore] , lunghezza )
    if tipo=='int':
        return padInt ( row[indiceValore] , lunghezza)
    if tipo=='dateIta2YYYYMMDD':
        return padDateIta2YYYYMMDD ( row[indiceValore] , lunghezza )
    raise IndexError("Errore: tipo non rinosciuto " + tipo)

def padString(valore : str,lunghezza : int,v=" "):
    return valore.ljust(lunghezza,v)

def padInt(valore : str,lunghezza : int,v="0"):
    return valore.rjust(lunghezza,v)

def padDateIta2YYYYMMDD(valore,lunghezza,v="0"):
    return valore  #TODO

def csv2fixedWithFile(dataFileInput, dataFileTracciato):
    fileOutput="";
    #per ogni riga del dataFileTracciato creo una lista con l'elenco dei campi
    listaCampi=[] # campi arrivano campo0;val;5;03365;abi
    for row in csv.reader(dataFileInput, delimiter=';'): #csv.DictReader(codecs.getreader('utf-8')(dataFileInput), delimiter=';'):
        campo={}
        campo["campo"]=row[0]
        campo["tipo"]=row[1]
        campo["lunghezza"]=row[2]
        campo["valore"]=row[3]
        try:
            campo["desc"]=row[4]
        except:
            campo["desc"]="no desc"
        #print("Riga: " + json.dumps(campo) )
        listaCampi.append(campo)
    #per ogni riga del file input csv
    reader= csv.reader(dataFileTracciato, delimiter=';')
    intestazioneInput=next(reader, None)  # skip the headers in intestazioneInput #print("Riga: " + json.dumps(intestazioneInput) )
    for row in reader: #for row in csv.DictReader(codecs.getreader('utf-8')(dataFileInput), delimiter=';'):
        stringaRiga="";
        #per ogni campo lo aggiungo prendendolo
        for campo in listaCampi:
            stringaRiga+=aggiungiCampoARiga(intestazioneInput, row,campo)
        fileOutput+=stringaRiga+"\n"
    return fileOutput

print(__name__)

with open("tracciato.csv","rt") as dataFileInput:
    with open("input.csv","rt") as dataFileTracciato:
        output=csv2fixedWithFile( dataFileInput.readlines() , dataFileTracciato.readlines() ) 
print(output)
with open('OUT.txt', 'w') as the_file:
  the_file.write(output)