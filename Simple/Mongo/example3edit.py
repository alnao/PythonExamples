import pymongo
from pymongo import MongoClient
#$ pip install pymongo
client = MongoClient('localhost',27017)
db = client.pythonexample 
persone_coll=db.persone 
res = persone_coll.update_one ( 
    {"nome":"Alberto", "cognome":"Nao"} , #query
    {"$set" : {"eta":37} } # $set è un opratore mongo
)
p=persone_coll.find_one({"nome":"Alberto", "cognome":"Nao"})
print(p)