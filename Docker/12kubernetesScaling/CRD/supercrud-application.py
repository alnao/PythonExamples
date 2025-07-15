from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import psycopg2
from datetime import datetime
import os
pod_name = os.getenv("HOSTNAME")

app = FastAPI()

# Connessione al DB PostgreSQL centrale
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "mydb"),
    user=os.getenv("DB_USER", "admin"),
    password=os.getenv("DB_PASSWORD", "secret"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432")
)
cursor = conn.cursor()

# Modello dati
class Item(BaseModel):
    id: int = None
    name: str
    description: str

# Crea tabella al primo avvio
cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    )
""")
conn.commit()

#def get_connection():
#    return psycopg2.connect(
#        host=os.getenv("DB_HOST", "localhost"),
#        port=os.getenv("DB_PORT", "5432"),
#        database=os.getenv("DB_NAME", "mydb"),
#        user=os.getenv("DB_USER", "admin"),
#        password=os.getenv("DB_PASSWORD", "secret")
#    )

    
@app.get("/")
def root():
    pod_name = os.getenv("HOSTNAME", "unknown-pod")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    description = f"Eseguito il {timestamp}"

    try:
        #conn = get_connection()
        #cur = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS logs (id SERIAL PRIMARY KEY, pod_name TEXT, description TEXT)")
        cursor.execute("INSERT INTO logs (pod_name, description) VALUES (%s, %s)", (pod_name, description))
        conn.commit()
        #cursor.close()
        #conn.close()
    except Exception as e:
        return {"pod": pod_name, "error": str(e)}

    return {"pod": pod_name, "message": "Insert OK"}

@app.get("/items", response_model=List[Item])
def read_items():
    cursor.execute("SELECT id, name, description FROM items")
    rows = cursor.fetchall()
    return [Item(id=r[0], name=r[1], description=r[2]) for r in rows]

@app.post("/items", response_model=Item)
def create_item(item: Item):
    cursor.execute("INSERT INTO items (name, description) VALUES (%s, %s) RETURNING id", (item.name, item.description))
    item.id = cursor.fetchone()[0]
    conn.commit()
    return item

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    cursor.execute("SELECT id, name, description FROM items WHERE id = %s", (item_id,))
    row = cursor.fetchone()
    if row:
        return Item(id=row[0], name=row[1], description=row[2])
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    conn.commit()
    return {"status": "deleted"}
