# Esempio 13 FastAPI with AuthJWT

Esempio minimale di autenticazione JWT con FastAPI, pronto per essere eseguito in Docker.

Nota: le credenziali sono salvate dentro ad un dizionario `fake_users_db` in-memory e non un database esterno, prevedere un database esterno se necessario!

## Struttura

- `app/main.py`: API FastAPI con:
  - `/register`: registra un utente in un finto DB in memoria
  - `/token`: login OAuth2 password flow e generazione access token JWT
  - `/me`: endpoint protetto che restituisce l'utente corrente
- `Dockerfile`: immagine Python 3.11 con FastAPI e Uvicorn.
- `requirements.txt`: dipendenze Python.

## Avvio locale (senza Docker)

```bash
cd Docker/13FastAPIAuthJWT
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Vai su `http://127.0.0.1:8000/docs` per provare le API.

## Build ed esecuzione con Docker

```bash
cd Docker/13FastAPIAuthJWT
docker build -t fastapi-auth-jwt .
docker run --rm -p 8000:8000 fastapi-auth-jwt
```

Poi apri `http://127.0.0.1:8000/docs`.


## Test generale
```bash

# Registra un utente:
curl -X POST "http://127.0.0.1:8000/register" -H "Content-Type: application/json" -d '{"username":"alnao","password":"Password123!","full_name":"Al Nao"}'

# Ottieni il token:
response=$(curl -X POST "http://127.0.0.1:8000/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=alnao&password=Password123!")
token=$(echo $response | jq -r .access_token)
echo "Token ottenuto: $token"

# Esecuzione api ME e service

curl "http://127.0.0.1:8000/me" -H "Authorization: Bearer $token"

curl "http://127.0.0.1:8000/service" -H "Authorization: Bearer $token"
#JSON con orario del server e messaggio di saluto personalizzato.
```





# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

