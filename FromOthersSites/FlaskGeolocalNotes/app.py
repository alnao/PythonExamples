from flask import Flask, render_template, request,redirect
import sqlite3 as sq

#see https://www.youtube.com/watch?v=w-rti-5KHME
"""
python3 app.py
"""

app=Flask(__name__)

@app.route("/")
def hello():
    return render_template("main.html")

@app.route("/api/notes")
def get_notes():
    #return [{"content":"testo","id":1,"lat":51.508964,"lng":-0.095577 }]
    db=sq.connect("data.db")
    cursor=db.cursor()
    cursor.execute("SELECT * FROM notes ")
    #return cursor.fetchAll()
    data = [
        {"content":row[1],"id":row[0],"lat":row[2],"lng":row[3] } 
        for row in cursor #.fetchAll()
    ]
    db.close()
    return data

@app.post("/api/notes")
def save_notes():
    content= request.form.get("content")
    lat= request.form.get("lat")
    lng= request.form.get("lng")
    print(content,lat,lng)
    db=sq.connect("data.db")
    cursor=db.cursor()
    cursor.execute("INSERT INTO notes (content,lat,lng) VALUES (?,?,?)" , (content,lat,lng))
    db.commit()
    db.close()
    return redirect("/")

app.run(debug=True,port=5001)