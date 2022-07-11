import pymongo
from pymongo import MongoClient
#$ pip install pymongo
client = MongoClient('localhost',27017)
#accedo/creo il DB
db = client.pythonexample  #se nomedb non c'è, lo crea
#collection
persone_coll=db.persone 
persone_coll.create_index( [ ("nome",pymongo.ASCENDING ) ] ) #crea indice mono-campo
persone_coll.create_index( [ ("cognome",pymongo.ASCENDING ) ] ) #crea indice mono-campo
persone_coll.create_index( [ ("computer",pymongo.ASCENDING ) ] ) #crea indice mono-campo anche se è un ARRAY
#crea un documento e lo inserisce
p1= { "nome":"Alberto", "cognome":"Nao", "eta":30, "computer": ["Cirilla","Levy"] }
persone_coll.insert_one( p1 )