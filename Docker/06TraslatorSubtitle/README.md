# Traslator Subtitle
Esempio preso dai video
- https://www.youtube.com/watch?v=-l7YocEQtA0 
- https://www.youtube.com/shorts/A-Ae5abgMmY

dove si costruisce una immagine docker con jupyter/tensorflow e si usano le librerie pyplot e transformers per tradurre un testo di sottotitoli nel formato srt

## tensorflow
Da ```https://hub.docker.com/r/jupyter/tensorflow-notebook``` scaricare l'immagine con i comandi
```bash
$ docker pull jupyter/tensorflow-notebook
$ docker run jupyter/tensorflow-notebook
``` 
Lanciando all'indirizzo ```http://127.0.0.1:8888/lab?token=xxxxx``` ritorna errore perchè manca il file di configurazione

Rilanciare con il comando
```bash
$ docker run -p 8042:8888  jupyter/tensorflow-notebook
```
e nella porta 
```http://localhost:8042/```
risponde correttamente inserendo il tocken che viene visualizzato in console.


### Codice di esempio
```python
from tensorflow.keras.datasets import mnist
(x_train,y_train),(x_test,y_test) = mnist.load_data()
import matplotlib.pyplot as plt
plt.imshow(x_train[0])
    si vede immagine
y_train[0]
    di cosa?
```

## Transformers
Sarebbe possibile lanciare 
```bash
!pip install transformers
```
ma lei non vuole, facciamo un ```docker compose``` creando il file ```compose.yaml``` e poi crea anche il ```Dockerfile``` per eseguire ```pip install transformers```
poi bisogna lanciare i comandi
```bash
$ docker-compose --version
$ docker compose up 
```
(notare che è corretto che sia senza trattino, se non presente bisogna installare il pacchetto ```docker-compose-plugin```)

Una volta lanciato risponde alla porta ```localhost:8042``` e funziona con la login indicata nel file di configurazione.


### Codice di esempio
Una volta copiato il file dei sottitoli in formato srt
```python
from transformers import pipeline
translator = pipeline("translation_en_to_fr")
translator2 = pipeline("translation_en_to_it")
fr = translator ("my name is Alberto and I come from Italy")
fr[0]['translation_text']
```
e
```python
import pysrt
from transformers import pipeline
translator = pipeline("translation_en_to_fr")
subs=pysrt.open("captions_english.srt")
for i in subs:
    fr_text=translator(i.text)[0]['translation_text']
    i.text=fr_text
subs.save("captions_frensh.srt")
```

## Docker-Hub
Per poter pubblicare l'immagine nell'hub nel dockerfile aggiunge
```dockerfile
COPY captions_english.srt ./
COPY Translator.ipynb ./
```
Poi sdu docker-hub crea un progetto "srt-translator" e lancia il comando
```bash
docker images --> <local-name>
docker image tag <local-name>:latest alnao/srt-translator:1.0
docker images
docker push alnao/srt-translator:1.0
```
Su docker-hub si dovrebbe vedere la nuova versione dell'immagine che può essere scaricata con
```bash
cd newdirectory
docker pull alnao/srt-translator:1.0
docker run -p 5042:8888 alnao/srt-translator:1.0
```

## Pulizia finale
Per pulire le immagini nel sistema
```bash
docker container prune
docker images
docker rmi chatbotsimple-transformers-notebook
docker rmi <NAME or ID>
docker images
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

