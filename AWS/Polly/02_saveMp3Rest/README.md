AWS Polly - 02_saveMp3Rest
==========================

Questo esempio è stato generato con il `alnao-ai-runner` e poi verificato e corretto manualmente. 

Descrizione
-----------
Esempio REST con Flask che riceve via JSON una lista di item:
`id, uuid, nome, pathS3, keyS3, testoDaLeggere`.
Per ogni item esegue la stessa logica di `01_saveMp3`:
- sintesi testo con AWS Polly in MP3
- upload MP3 su S3 (`pathS3` bucket, `keyS3` key)
- scrittura `execution.log` sui bucket coinvolti

Prerequisiti
------------
- Python 3.9+
- Credenziali AWS valide
- Permessi IAM: `polly:SynthesizeSpeech`, `s3:PutObject`

Installazione
-------------
    pip install -r requirements.txt

Avvio
-----
    python main.py

Server attivo su:
    http://localhost:8002

Endpoint
--------
- `GET /` UI Bootstrap 5 + Font Awesome per test manuale
- `GET /api/health` health check
- `POST /api/synthesize` endpoint REST principale

Esempio `curl`
--------------
```
curl -X POST "http://localhost:8002/api/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "voice_id": "Bianca",
    "engine": "neural",
    "items": [
      {
        "id": "1",
        "uuid": "abc-123",
        "nome": "welcome",
        "pathS3": "my-bucket",
        "keyS3": "audio/welcome.mp3",
        "testoDaLeggere": "Benvenuto nel sistema"
      }
    ]
  }'
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

