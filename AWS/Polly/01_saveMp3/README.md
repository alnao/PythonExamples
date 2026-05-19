AWS Polly – Save MP3 to S3
==========================

Questo esempio è stato generato con il `alnao-ai-runner` e poi verificato e corretto manualmente. 

Descrizione
-----------
Applicazione Flask che riceve una lista di elementi
(id, uuid, nome, pathS3, keyS3, testoDaLeggere), sintetizza
ogni testo con AWS Polly (formato MP3) e carica il file audio
sul bucket Amazon S3 indicato.
In aggiunta:
- salva `execution.log` su ogni bucket coinvolto
- visualizza il log nella UI
- permette il download MP3 direttamente dalla UI

Prerequisiti
------------
- Python 3.9+
- Credenziali AWS configurate (aws configure) o variabili d'ambiente
  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
- Il bucket S3 deve già esistere e il profilo IAM deve avere i permessi:
    polly:SynthesizeSpeech
    s3:PutObject
    s3:GetObject

Installazione
-------------
    pip install -r requirements.txt

Avvio
-----
    python main.py

Aprire il browser su:  http://localhost:8001

Variabili d'ambiente opzionali
-------------------------------
    AWS_PROFILE   (default: "default")
    AWS_REGION    (default: "eu-west-1")

API
---
  GET  /          – Interfaccia web
  GET  /voices    – Lista voci Polly disponibili
                    ?language_code=it-IT  (opzionale)
  GET  /logs      – Legge execution.log da S3
                    ?bucket=my-bucket&key=execution.log
  GET  /download-mp3 – Scarica un MP3 da S3
                    ?bucket=my-bucket&key=audio/file.mp3
  POST /synthesize – Sintetizza e salva su S3
    Body JSON:
    {
      "voice_id": "Bianca",
      "engine":   "neural",
      "items": [
        {
          "id":             "1",
          "uuid":           "abc-123",
          "nome":           "benvenuto",
          "pathS3":         "my-bucket",
          "keyS3":          "audio/benvenuto.mp3",
          "testoDaLeggere": "Benvenuto nel sistema!"
        }
      ]
    }

    Risposta:
    {
      "results": [
        {
          "id":      "1",
          "uuid":    "abc-123",
          "nome":    "benvenuto",
          "s3_uri":  "s3://my-bucket/audio/benvenuto.mp3",
          "bucket":  "my-bucket",
          "key":     "audio/benvenuto.mp3",
          "status":  "success",
          "message": "MP3 salvato su S3"
        }
      ],
      "log_uploads": [
        {
          "bucket": "my-bucket",
          "status": "success",
          "key": "execution.log"
        }
      ]
    }



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

