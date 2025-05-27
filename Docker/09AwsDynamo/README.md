# Esempio 09 AWS Dynamo
Un sistema che usa aws dynamo con una tabella chiamata "alnao-persone" con campi nome, cognome, eta, data nascita e codice fiscale.  un microservizio sviluppato con python fastapi che espone delle api crud, e un microfrontend sviluppato con python flask che consuma le api e che usa bootstrap come libreria grafica. vorrei usare tutto con docker e docker-comose e kubernetes e minibube e heml. voglio poterlo usare nel mio computer con tutto docker (anche aws dynamo) e anche vorrei usarlo su un aws remoto.


## Sviluppo
Struttura del progetto base:
```
│
├── create.table
│   ├── create_table.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── fastapi-microservice/        # Microservizio FastAPI
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
│
├── flask-microfrontend/         # Microfrontend Flask
│   ├── templates/
│   ├── static/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── helm/                        # TODO Configurazioni Helm TODO-TBD
│   └── alnao-app/
│       └── templates/
│       └── Chart.yaml
│
├── docker-compose.yml           # Ambiente locale con DynamoDB
└── README.md
```


## Dynamo locale
Puoi usare l'immagine ufficiale di Amazon **amazon/dynamodb-local**:
```
docker run -d --name dynamodb-local-container -p 8000:8000 amazon/dynamodb-local
```
Comandi da eseguire
```
aws dynamodb list-tables --endpoint-url http://localhost:8000
aws dynamodb create-table --table-name Persone --attribute-definitions AttributeName=id,AttributeType=S --key-schema AttributeName=id,KeyType=HASH --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 --endpoint-url http://localhost:8000
aws dynamodb put-item --table-name Persone --item '{"id": {"S": "1"},"nome": {"S": "Mario Rossi"},"eta": {"N": "30"}}' --endpoint-url http://localhost:8000
aws dynamodb scan --table-name Persone --select "COUNT" --endpoint-url http://localhost:8000
aws dynamodb put-item --table-name Persone --item '{"id": {"S": "2"}, "nome": {"S": "Luigi Bianchi"}, "eta": {"N": "25"}}' --endpoint-url http://localhost:8000
aws dynamodb scan --table-name Persone --endpoint-url http://localhost:8000
aws dynamodb list-tables --endpoint-url http://localhost:8000

docker stop dynamodb-local-container
docker rm dynamodb-local-container

docker run -d -p 8000:8000 -v $(pwd)/dynamodb-data:/home/dynamodblocal/data --name dynamodb-local-container amazon/dynamodb-local
```

## Comandi per il rilascio
Per eseguire in locale
```
docker-compose up --build
```
E l'interfaccia è su 
```
http://localhost:8012/
```
La tabella è disponibile con il comando 
```
aws dynamodb list-tables --endpoint-url http://dynamodb-local:8010
aws dynamodb scan  --table-name  alnao-persone  --endpoint-url http://dynamodb-local:8010
```

## Nota sulle porte
Quando usi docker-compose e hai due servizi (ad esempio un backend API e un frontend o un altro servizio che lo chiama), la rete interna di Docker Compose ti permette di comunicare tra i container usando il nome del servizio definito nel file docker-compose.yml. Situazione: Hai due servizi:
```
# docker-compose.yml
services:
    api-service:
    build: ./api
    ports:
        - "8010:8000"

    other-service:
    build: ./other
```
- Il primo (api-service) espone un'API su porta 8000 all'interno del container.
- La porta è mappata come "8010:8000, quindi dall'esterno puoi accedere a http://localhost:8010.
- Vuoi che il secondo servizio (other-service) chiami le API di api-service.
Risposta breve:
- Il secondo servizio deve usare:	http://api-service:8000
- Non localhost:8010, né localhost:8000. Usa sempre il nome del servizio (api-service) e la porta interna (8000). 
Spiegazione dettagliata
- Docker Compose crea automaticamente una rete virtuale condivisa tra tutti i servizi definiti nello stesso file.
- All'interno di questa rete ogni servizio è accessibile dagli altri tramite il proprio nome (quello sotto services:). Le porte sono riferite a quelle interne al container, non a quelle mappate sull'host (8000, non 8010).
- Comandi per la verifica 
    ```
	docker exec -it other-service_container_id bash
	apt update && apt install -y curl
	curl http://api-service:8000/hello
    ```
- Nota: Se provassi a usare localhost:8010 da dentro il container other-service, non funzionerebbe , perché localhost si riferisce al container stesso, non ad api-service. L'unica volta in cui useresti localhost:8010 è dal tuo computer host (il tuo laptop/desktop), per esempio via browser o curl locale.


## Esecuzione con Minikube
Partendo dal `docker-compose` funzionante si usa `kompose convert` per convertire i file depositati nella cartella minikube.
Poi bisogna lanciare i comandi
```
minikube start --driver=docker --memory=2048 --cpus=2
...
kubectl apply -f ./minikube/dynamodb-local-service.yaml 
kubectl apply -f ./minikube/fastapi-service.yaml 
kubectl apply -f ./minikube/flask-frontend-service.yaml
    kubectl apply -f ./minikube/create-table-deployment.yaml
    kubectl delete deployment create-table
kubectl apply -f ./minikube/dynamodb-local-deployment.yaml
kubectl apply -f ./minikube/fastapi-deployment.yaml
kubectl apply -f ./minikube/flask-frontend-deployment.yaml

kubectl port-forward svc/flask-frontend 8032:5000

http://localhost:8012

kubectl get services
kubectl delete service dynamodb-local
kubectl delete service fastapi
kubectl delete service flask-frontend
kubectl get deployments
kubectl delete deployment dynamodb-local
kubectl delete deployment fastapi
kubectl delete deployment flask-frontend

minikube stop
```

# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*