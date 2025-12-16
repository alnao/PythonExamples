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
    ```bash
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
    ```bash
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
    ```bash
    kubectl get pods
    minikube ip
    kubectl get services
    kubectl get pvc
    kubectl get deployments
    ```
- Verifica del mysql
    ```bash
    kubectl get svc py-esempio08-mysql-svc  -o wide
    kubectl get pods -l app=py-esempio08-mysql -o wide
    ```
- Verifica del flask
    ```bash
    curl http://$(minikube ip):$(kubectl get service py-esempio08-flask-service -o jsonpath='{.spec.ports[0].nodePort}')
    curl http://$(minikube ip):$(kubectl get service py-esempio08-flask-service -o jsonpath='{.spec.ports[0].nodePort}')/persone
    ```   
- Fermare tutto
    ```bash
    kubectl delete deployment py-esempio08-flask-app
	kubectl delete deployment py-esempio08-mysql
	kubectl delete service py-esempio08-flask-service
    kubectl delete service py-esempio08-mysql-svc
    kubectl delete pvc py-esempio08-mysql-pvc    
    ```

- Verifica connessione tra POD flask e POD mysql
    ```bash
    kubectl exec -it py-esempio08-flask-app-59966cdbdb-c8sk4 -- bash
    > curl py-esempio08-mysql-svc:3306
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

