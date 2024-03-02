from flask import Flask, render_template, request,redirect, url_for, session,g #g=global see documentation
import sqlite3 as sq
import hashlib

"""
see https://www.youtube.com/watch?v=ud_nq9lapF4 Python webapp: autenticazione utenti con flask
    pip install flask

To run 
$ python3 ./app.py
importante: per il collegamento al database è importante lanciare il comando dalla stessa cartella

or
$ python3 -mflask run -p 5001
without app.run(debug=True)
"""

app=Flask(__name__)
app.secret_key=b'1234567890' #to session is necessary, secret is secret

"""
-- Promemoria da VsCode: "> SQLite Open database" 
create table users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL
);
INSERT INTO users (username, password) VALUES ('alnao','......');

creare la password cryptata lanciare il comando 
import hashlib
print ( hashlib.sha256(b"bellissimo").hexdigest() ) 

"""
#con G creo e distruggo la connessione al DB
@app.before_request
def before_request():
    db = sq.connect("users.db")
    g.db=db
@app.after_request
def after_request(response):
    g.db.close()
    return response
def check_password(username,password,db):
    if db is None:
        return False
    cur = db.cursor()
    cur.execute("SELECT password FROM users WHERE username=?",(username,))
    rows=cur.fetchone()
    if rows is None:
        return False
    return rows[0]==password

@app.get ("/")
def home():
    return render_template("home.html")

@app.get ("/welcome")
def welcome():
    if 'username' not in session:
        return redirect(url_for("login")) 
    username=session['username']
    return render_template("welcome.html",username=username)

@app.route("/login",methods=["GET","POST"]) #@app.get & @app.post
def login():
    if request.method=="GET":
        return render_template("login.html")
    else:
        username=request.form["username"]
        password=request.form["password"]
        password=hashlib.sha256(password.encode()).hexdigest()
        if check_password(username,password,g.db):
            session['username']=username
            #g.user=username
            return redirect(url_for("welcome"))
        else:
            return "<p>Wrong credentials</p><a href='./login'>Login</a>"

@app.get("/logout")
def logout():
    session.pop("username",None)
    return redirect(url_for("login"))


if __name__=="__main__": #note must be after all @app.route definition
    app.run(host="0.0.0.0", port=5001, debug=True)

