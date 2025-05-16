from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)
API_URL = os.getenv("API_URL", "localhost:8000")


@app.route('/')
def index():
    try:
        response = requests.get(f"{API_URL}/persone")
        persone = response.json()
    except:
        persone = []
    return render_template("index.html", persone=persone)

@app.route('/aggiungi', methods=["POST"])
def aggiungi():
    persona = {
        "codice_fiscale": request.form["cf"],
        "nome": request.form["nome"],
        "cognome": request.form["cognome"],
        "eta": int(request.form["eta"]),
        "data_nascita": request.form["data_nascita"]
    }
    requests.post(f"{API_URL}/persone/", json=persona)
    return redirect(url_for("index"))

@app.route('/elimina/<codice_fiscale>', methods=["POST"])
def elimina_persona(codice_fiscale):
    requests.delete(f"{API_URL}/persone/{codice_fiscale}")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)