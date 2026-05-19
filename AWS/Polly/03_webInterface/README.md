AWS Polly - 03_webInterface
==========================

Interfaccia web completa per AWS Polly con supporto a singolo elemento,
lista di elementi, JSON diretto e visualizzazione degli MP3 generati su S3.

Sommario: 03 è un superset di 02. La logica di sintesi/upload è copia-identica; 03 aggiunge endpoint per elencare voci, listare MP3 da S3 e fare download diretto, con send_file. Il template HTML probabilmente rispecchia questa UI più ricca.

Questo esempio è stato generato con il `alnao-ai-runner` e poi verificato e corretto manualmente. 

Prerequisiti
------------
- Python 3.10+
- Credenziali AWS configurate (aws configure oppure variabile AWS_PROFILE)
- IAM policy: polly:SynthesizeSpeech, s3:PutObject, s3:GetObject, s3:ListBucket

Avvio
-----
  cd AWS/Polly/03_webInterface
  pip install -r requirements.txt
  python main.py

Oppure con variabili d'ambiente personalizzate:
  AWS_PROFILE=myprofile AWS_REGION=eu-west-1 python main.py

L'app sarà disponibile su http://localhost:8003

Endpoint API
------------
```
  GET  /                             Interfaccia web principale
  GET  /api/health                   Health check
  GET  /api/voices?language_code=it  Lista voci Polly disponibili
  POST /api/synthesize               Sintetizza lista item e salva su S3
  GET  /api/list-mp3?bucket=...      Lista file MP3 in un bucket S3
  GET  /api/download-mp3?bucket=...&key=...  Download MP3 da S3
```

Payload POST /api/synthesize
-----------------------------
```
  {
    "voice_id": "Bianca",
    "engine":   "neural",
    "items": [
      {
        "id":            "1",
        "uuid":          "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx",
        "nome":          "benvenuto",
        "pathS3":        "my-polly-bucket",
        "keyS3":         "audio/benvenuto.mp3",
        "testoDaLeggere": "Benvenuto nel sistema AWS Polly."
      }
    ]
  }
```
Funzionalità interfaccia
-------------------------
- Tab "Singolo elemento": form per un singolo item con generazione UUID automatica
- Tab "Lista elementi":   tabella con aggiunta/rimozione righe
- Tab "JSON diretto":     editor JSON con formattazione e mostra-esempio
- Sezione MP3 generati:  lista tutti gli MP3 nel bucket con download e preview audio
- Upload automatico di execution.log su S3 ad ogni sintesi



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

