import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pymysql
import time
import hashlib
import re
import os
import uvicorn
app = FastAPI()
origins = ["*"] # Allow all origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Feedback(BaseModel):
    token: str
    name: str
    email: str
    title: str
    message: str

class AddItem(BaseModel):
    token: str
    id: int
    name: str
    description: Optional[str] = None
    price: float
    quantity: int

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    quantity: int


load_dotenv()
host = os.getenv("HOST")
user = os.getenv("ID")
password = os.getenv("PASSWORD")
db = os.getenv("DB")
# Connect to MySQL database
connection = pymysql.connect(
    host=host,
    user=user,
    password=password,
    db=db,
)

current_token = None


def validate_email(email):
    print("Validating email", email)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True
    else:
        return False


@app.post("/login/")
async def login(request: Request):
    req = await request.json()
    username = req['username']
    password = req['password']
    if username == "admin" and password == "admin":
        timestamp = str(time.time())
        token = hashlib.sha256(timestamp.encode()).hexdigest()
        global current_token
        current_token = token
        return {"result": True, "token": token}
    else:
        return {"result": False}
# Create

@app.post("/addItem/")
async def create_item(item: AddItem):
    try:
        if item.token != current_token:
            raise HTTPException(status_code=403, detail="Invalid token")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM websec WHERE id=%s", (item.id,))
        result = cursor.fetchone()
        if result is not None:
            raise HTTPException(status_code=400, detail="Item already exists")
        cursor.execute("INSERT INTO websec (id, name, description, price, quantity) VALUES (%s, %s, %s, %s, %s)",
                       (item.id, item.name, item.description, item.price, item.quantity))
        connection.commit()
        return {"result": True}
    except Exception as e:
        print(e)
        return {"result": False}


@app.post("/sendMessage/")
async def send_message(item: Feedback):
    try:
        if item.token != current_token:
            raise HTTPException(status_code=403, detail="Invalid token")
        if not validate_email(item.email):
            raise HTTPException(status_code=400, detail="Invalid email")
        cursor = connection.cursor()
        timestamp = str(datetime.datetime.now())
        print("Request", item)
        cursor.execute("INSERT INTO contact_messages (id, name, email, title, message) VALUES (%s, %s, %s, %s, %s)",
                       (timestamp, item.name, item.email, item.title, item.message))
        connection.commit()
        return {"result": True}
    except Exception as e:
        print(e)
        return {"result": False}

# Read all
@app.post("/items/")
async def read_all_items(request: Request):
    try:
        req = await request.json()
        print("Request", req)
        token = req['token']
        if token != current_token:
            raise HTTPException(status_code=403, detail="Invalid token")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM websec")
        results = cursor.fetchall()
        items = []
        for result in results:
            item = Item(id=result[0], name=result[1], description=result[2], price=result[3], quantity=result[4])
            items.append(item)
        return {"result": True, "items": items}
    except Exception as e:
        print(e)
        return {"result": False}

# Read one
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM websec WHERE id=%s", (item_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item = Item(id=result[0], name=result[1], description=result[2], price=result[3], quantity=result[4])
    return {"item": item}

# Update
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM websec WHERE id=%s", (item_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute("UPDATE websec SET name=%s, description=%s, price=%s, quantity=%s WHERE id=%s",
                   (item.name, item.description, item.price, item.quantity, item_id))
    connection.commit()
    item.id = item_id
    return {"message": "Item updated", "item": item}

# Delete
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM websec WHERE id=%s", (item_id,))
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute("DELETE FROM websec WHERE id=%s", (item_id,))
    connection.commit()
    return {"message": "Item deleted"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)