from flask import Flask, jsonify, request
from models import db, User

app = Flask(__name__)

# Configurazione del database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db:5432/mydatabase'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inizializza il database
db.init_app(app)

# Crea le tabelle al primo avvio
with app.app_context():
    db.create_all()

# Rotta per creare un nuovo utente
@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    new_user = User(username=data['username'],name=data['name'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created", "user": new_user.username}), 201

# Rotta per ottenere tutti gli utenti
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{"id": user.id, "username": user.username , "name" : user.name} for user in users])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)