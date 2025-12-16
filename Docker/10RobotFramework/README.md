# Esempio 10 Robot Framework
Esempio di progettino con un robotframework che esegue un test su un processo che simula una scrittura su una coda kafka e lettura su una tabella dynamo.
Struttura del progetto
│
├── robotLib/                    # cartella con librerie robot framework
│   ├── DynamoLibrary.py         # libreria per aws dynamodb
│   └── KafkaLibrary.py          # libreria per kafka
│
├── server/                      # cartella con i componenti per creare i server: applicazione, dynamoDb, kafka
│   ├── application/                 # piccola applicazione/consumer in python che legge da kafka e scrive in una tabella dynamoù
│   │   ├── Dockerfile               # docker file dell'applicazione che installa anche AWS (per fare qualche prova)
│   │   └── kafka_consumer.py        # codice dall'applicazione
│   ├── frontend/                    # piccola applicazione in python-flask per visualizzare i dati dynamo esposta su porta 5042
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── templates/
│   │       └── index.html
│   ├── check-dynamodb.py        # script python per verificare cosa c'è in tabella
│   └── docker-compose.yml       # docker compose del progetto
│
├── esempio10.robot              # script con i test di robot framework
├── run-test.sh                  # script sh per lanciare i test (dell'esempio10)
├── test-install.robot           # script con test base per verificare se la libreria python e robot-framework è correttamente installata
└── README.md

## Installazione
Comandi per l'installazione di *RobotFramework* su server dove è già presente python3 (3.9+):
```bash
pip3 install --user robotframework robotframework-jsonlibrary robotframework-requests robotframework-databaselibrary boto3 kafka-python requests PyMySQL psycopg2-binary --break-system-packages
robot --outputdir robotoutput test-install.robot
```

## Avvio server e applicazione 
Il docker-compose dentro la cartella server contiene
- **DynamoDb**: server che viene esposto su porta 8000 
- Script Dynamo (init-dynamodb): script AWS-CLI che crea la tabella (vedere l'immagine `amazon/aws-cli:latest` )
- **Kafka**: server esposto su porta 9092 con un bel healthcheck
- init-kafka: script che crea un topic 
- **kafka-ui**: frontend per la gestione di kafka, esposto al `localhost:9000`
- Zookeeper: *qualunque cosa serva*
- Applicazione e frontend


Per avviare il server posizionarsi nella cartella server e lanciare il docker-compose:
```bash
docker-compose build --no-cache
docker-compose up
docker-compose ps
```
Poi accedere alla UI di Kafka: 
```
http://localhost:9000
```
Ricordandosi che i server sono disponibili nelle porte:
- Kafka: localhost:9092
- DynamoDB: localhost:8008
- Kaffa UI: localhost:9000
- Zookeeper: localhost:2181


### Comandi dynamo

Lo script di avvio crea automaticamente la tabella ma è possibile lanciare i comandi anche da riga di comando.


Attenzione che non funzionano perchè nello script di creazione ci sono delle *fakecredential* e quindi è stato fatto uno script dedicato `check-dynamodb.py` ma qui si riportano ugualmente i comandi per praticità:
```bash
# lista di tutte le tabelle
aws dynamodb list-tables --endpoint-url http://localhost:8000 --region us-east-1 --no-cli-pager
aws dynamodb list-tables --endpoint-url http://dynamodb-local:8000 --region us-east-1 --no-cli-pager
# creazione della tabella
aws dynamodb create-table \
    --table-name alberto-dy2 \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:8000 \
    --region us-east-1 \
    --no-cli-pager
aws dynamodb describe-table \
    --table-name alberto-dy2 \
    --endpoint-url http://localhost:8000 \
    --region us-east-1 \
    --no-cli-pager
# inserimento di un elemento
aws dynamodb put-item \
    --table-name alberto-dy2 \
    --item '{"id":{"S":"abc12345"},"value":{"S":"test"},"timestamp":{"S":"2025-01-01T10:00:00Z"}}' \
    --endpoint-url http://localhost:8000 \
    --region us-east-1 \
    --no-cli-pager
# scan e get-item nella tabella    
aws dynamodb scan \
    --table-name alberto-dy2 \
    --endpoint-url http://localhost:8000 \
    --region us-east-1 \
    --no-cli-pager
aws dynamodb get-item \
    --table-name alberto-dy2 \
    --key '{"id":{"S":"abc123"}}' \
    --endpoint-url http://localhost:8008 \
    --region us-east-1 \
    --no-cli-pager
```
Se si vuole creare solo il dynamo dal docker compose eseguire il comando
```bash
docker compose up --build 'init-dynamodb' 
```

### Applicazione
EEsempio di applicazione Consumer che prende i messaggi dal topic Kafka e scrive su Dynamo (cioè quello che testa il robot)
Comando per l'esecuzone
``` bash
pip3 install -r requirements.txt --break-system-packages
python3 kafka_consumer.py
```
Oppure lanciando il docker*
```bash
docker build -t kafka-consumer-app .
docker run \
  -e KAFKA_BOOTSTRAP_SERVERS="kafka:9092" \
  -e DYNAMODB_ENDPOINT="http://dynamodb-local:8000" \
  -e MAX_WORKERS=1 \
  --network server_kafka-network \
  kafka-consumer-app
```
Nota*: questo potrebbe **NON** funzionare se lanciato come `docker` fuori dal `docker-compose` perchè le reti sono diverse.


Il frontend è esposto su porta `5042`

### Comandi vari e pulizia finale
- Avvia tutti i servizi
    ```bash
    docker-compose up -d
    ```
- Visualizza i log
    ```bash
    docker-compose logs -f
    ```
- Ferma tutti i servizi
    ```bash
    docker-compose down
    ```
- Ferma e rimuove i volumi (attenzione: cancella i dati!)
    ```bash
    docker-compose down -v
    ```
- Riavvia un singolo servizio
    ```bash
    docker-compose restart kafka
    ```
- Pulizia del sistema operativo
    ```bash
    docker container prune
    docker volume prune
	docker network prune
	docker image prune -a
    ```
    *occhio che questo esempio occupa molto spazio perchè il server è bello grosso quindi conviene sempre pulire un po' dopo l'esecuzione*


# Esecuzione robot framework
Comando per l'esecuzione dei test Robot Framework:
```bash
sh run-tests.sh
```
E vedere la cartella di output `robotoutput` il risultato dei test.






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

