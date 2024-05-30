# see https://fastapi.tiangolo.com/tutorial/first-steps/
# see https://fastapi.tiangolo.com/tutorial/schema-extra-example/
# see https://realpython.com/fastapi-python-web-apis/

# TO RUN uvicorn main:app --reload
# file must be main.py, 
# http://127.0.0.1:8000
# http://127.0.0.1:8000/docs

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}
@app.get("/itemsInt/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

from typing import Optional
from pydantic import BaseModel
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None
@app.post("/itemsPost/")
async def create_item(item: Item):
    return item