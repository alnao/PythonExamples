import pymongo
from pymongo import MongoClient
#$ pip install pymongo
client = MongoClient('localhost',27017)
db = client.pythonexample 
persone_coll=db.persone 
#fine_one senza parametri trova il primo
p=persone_coll.find_one()
print(p)
#find con query
persone = persone_coll.find( { "computer": "Cirilla" } )
for persona in persone:
	print(persona)
#condition and filter
p=persone_coll.find_one( {"eta": {"$gt" : 35} } ) # $gt operatore >
print(p)