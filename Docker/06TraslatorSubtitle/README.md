# Traslator Subtitle
Esempio preso dai video
- https://www.youtube.com/watch?v=-l7YocEQtA0 
- https://www.youtube.com/shorts/A-Ae5abgMmY

dove si costruisce una immagine docker con jupyter/tensorflow e si usano le librerie pyplot e transformers per tradurre un testo di sottotitoli nel formato srt

## tensorflow
Da ```https://hub.docker.com/r/jupyter/tensorflow-notebook``` scaricare l'immagine con i comandi
```
$ docker pull jupyter/tensorflow-notebook
$ docker run jupyter/tensorflow-notebook
``` 
Lanciando all'indirizzo ```http://127.0.0.1:8888/lab?token=xxxxx``` ritorna errore perchè manca il file di configurazione

Rilanciare con il comando
```
$ docker run -p 8042:8888  jupyter/tensorflow-notebook
```
e nella porta 
```http://localhost:8042/```
risponde correttamente inserendo il tocken che viene visualizzato in console.


### Codice di esempio
```
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
```
!pip install transformers
```
ma lei non vuole, facciamo un ```docker compose``` creando il file ```compose.yaml``` e poi crea anche il ```Dockerfile``` per eseguire ```pip install transformers```
poi bisogna lanciare i comandi
```
$ docker-compose --version
$ docker compose up 
```
(notare che è corretto che sia senza trattino, se non presente bisogna installare il pacchetto ```docker-compose-plugin```)

Una volta lanciato risponde alla porta ```localhost:8042``` e funziona con la login indicata nel file di configurazione.


### Codice di esempio
Una volta copiato il file dei sottitoli in formato srt
```
from transformers import pipeline
translator = pipeline("translation_en_to_fr")
translator2 = pipeline("translation_en_to_it")
fr = translator ("my name is Alberto and I come from Italy")
fr[0]['translation_text']
```
e
```
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
```
COPY captions_english.srt ./
COPY Translator.ipynb ./
```
Poi sdu docker-hub crea un progetto "srt-translator" e lancia il comando
```
docker images --> <local-name>
docker image tag <local-name>:latest alnao/srt-translator:1.0
docker images
docker push alnao/srt-translator:1.0
```
Su docker-hub si dovrebbe vedere la nuova versione dell'immagine che può essere scaricata con
```
cd newdirectory
docker pull alnao/srt-translator:1.0
docker run -p 5042:8888 alnao/srt-translator:1.0
```

## Pulizia finale
Per pulire le immagini nel sistema
```
docker container prune
docker images
docker rmi chatbotsimple-transformers-notebook
docker rmi <NAME or ID>
docker images
```



# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*