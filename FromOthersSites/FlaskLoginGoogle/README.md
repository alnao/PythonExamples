# FlaskLoginGoogle
Esempio preso dal sito:
[realpython.com/flask-google-login/](https://realpython.com/flask-google-login/)


Vedere configurazione configurazione di Google api-Credenziali di tipo **OAuth 2.0**: 
[console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
dopo devono essere configurate le due variabili di ambiente 
```GOOGLE_CLIENT_ID``` e ```GOOGLE_CLIENT_SECRET``` 

## Comandi per l'installazione:
```
pip install -r requirements.txt
pip freeze
```

## Comandi per la creazione del db:
```
CREATE TABLE user (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  profile_pic TEXT NOT NULL
);
```
## Comandi per l'esecuzione:
```
python app.py
```


