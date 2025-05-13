# Esempio 08 CrudMySqlMinikubernetes
Creazione di un microservizio in Python con Flask che accede a un database MySQL, tutto orchestrato con Docker, Kubernetes e Minikube.


Si intende solo progetto di esempio migliorabile sotto molti aspetti.


Struttura del progetto:
```
├── app/                      
│   ├── app.py                # Applicazione Flask
│   └── requirements.txt      
├── Dockerfile                
├── k8s/                      # Configurazioni Kubernetes
│   ├── mysql-pvc.yaml        
│   ├── mysql-deployment.yaml
│   ├── mysql-init-configmap.yaml
│   ├── mysql-service.yaml
│   ├── flask-deployment.yaml
│   └── flask-service.yaml
└── README.md
```

# Comandi 
- Avvio con Docker , login e push su repository su DockerHub (necessario che docker sia presente nel sistema e che sia disponibile una utenza DockerHub):
    ```
    docker login
    docker build -t py-esempio08-flask-mysql:1.0 .
    docker tag py-esempio08-flask-mysql:1.0 alnao/py-esempio08-flask-mysql:1.0
    docker push alnao/py-esempio08-flask-mysql:1.0

    ```
    è possibile verificare su:
    ```
    https://hub.docker.com/repository/docker/alnao/py-esempio08-flask-mysql/general
    ```
- Avvio di minikube (necessario che Kubernetes e Minikube sia presente e funzionate nel sistema):
    ```
    minikube start --driver=docker --memory=2048 --cpus=2
    # Mysql
    kubectl apply -f k8s/mysql-pvc.yaml
    kubectl apply -f k8s/mysql-init-configmap.yaml
    kubectl apply -f k8s/mysql-deployment.yaml
    kubectl apply -f k8s/mysql-service.yaml
    #Flask
    kubectl apply -f k8s/flask-deployment.yaml
    kubectl apply -f k8s/flask-service.yaml
    ```
- Verifica di cosa è stato avviato
    ```
    kubectl get pods
    minikube ip
    kubectl get services
    kubectl get pvc
    kubectl get deployments
    ```
- Verifica del mysql
    ```
    kubectl get svc py-esempio08-mysql-svc  -o wide
    kubectl get pods -l app=py-esempio08-mysql -o wide
    ```
- Verifica del flask
    ```
    curl http://$(minikube ip):$(kubectl get service py-esempio08-flask-service -o jsonpath='{.spec.ports[0].nodePort}')
    curl http://$(minikube ip):$(kubectl get service py-esempio08-flask-service -o jsonpath='{.spec.ports[0].nodePort}')/persone
    ```   
- Fermare tutto
    ```
    kubectl delete deployment py-esempio08-flask-app
	kubectl delete deployment py-esempio08-mysql
	kubectl delete service py-esempio08-flask-service
    kubectl delete service py-esempio08-mysql-svc
    kubectl delete pvc py-esempio08-mysql-pvc    
    ```

- Verifica connessione tra POD flask e POD mysql
    ```
    kubectl exec -it py-esempio08-flask-app-59966cdbdb-c8sk4 -- bash
    > curl py-esempio08-mysql-svc:3306
    ```


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*