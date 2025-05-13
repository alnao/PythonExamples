from flask import Flask, request, jsonify
import mysql.connector
import os

app = Flask(__name__)

# Configurazione database
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'mysql'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'password123'),
        database=os.getenv('DB_NAME', 'testdb')
    )
    return conn

# COMMENTATO perchè c'è il file mysql-init che crea la tabella
## Crea la tabella Persone se non esiste
#@app.route('/create_table', methods=['GET'])
#def create_table():
#    print("Creating table...")
#    conn = get_db_connection()
#    cursor = conn.cursor()
#    cursor.execute("""
#        CREATE TABLE IF NOT EXISTS Persone (
#            id INT AUTO_INCREMENT PRIMARY KEY,
#            nome VARCHAR(100) NOT NULL,
#            cognome VARCHAR(100) NOT NULL
#        )
#    """)
#    conn.commit()
#    cursor.close()
#    conn.close()
#    return jsonify({"messaggio": "Tabella aggiunta"}), 201

# Chiama create_table() all'avvio
#create_table()  # 👈 Chiamata manuale all'avvio

@app.route('/persone', methods=['GET'])
def get_persone():
    print("Fetching all records...")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Persone")
    risultati = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(risultati)

@app.route('/persone', methods=['POST'])
def add_persona():
    print("Adding a new record...")
    dati = request.get_json()
    nome = dati.get('nome')
    cognome = dati.get('cognome')

    if not nome or not cognome:
        return jsonify({"errore": "Nome e cognome sono richiesti"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Persone (nome, cognome) VALUES (%s, %s)", (nome, cognome))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"messaggio": "Persona aggiunta", "nome": nome, "cognome": cognome}), 201

@app.route('/')
def index():
    print("Index page accessed")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT NOW()")
    result = cursor.fetchone()
    return f"Database time: {result[0]}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

# docker run -d -p 5000:5000 --name flaskapp --network mynetwork flaskapp