from flask import Flask, request,jsonify

app=Flask(__name__)

@app.get("/test")
def test():
    return "test OK"

persone = [
    { 'nome': 'Alberto', 'cognome': 'Nao' }
]

@app.route('/persone')
def get_persone():
    return jsonify(persone)

@app.route('/persone', methods=['POST'])
def add_persona():
    persone.append(request.get_json())
    return '', 201

if __name__=="__main__": #note must be after all @app.route definition
    app.run(host="0.0.0.0", port=5001, debug=True)
