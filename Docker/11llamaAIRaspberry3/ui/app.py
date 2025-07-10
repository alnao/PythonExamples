# app.py migliorato
from flask import Flask, request, jsonify, render_template
import requests
import os

app = Flask(__name__, static_folder='.', static_url_path='')

LLAMA_SERVER = os.getenv('LLAMA_SERVER', 'http://localhost:8080')

@app.route('/')
def index():
    #return send_from_directory('.', 'index.html')
    return render_template("index.html")

@app.route('/api/completion', methods=['POST'])
def completion():
    try:
        response = requests.post(
            f"{LLAMA_SERVER}/completion",
            json=request.json,
            timeout=30
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})