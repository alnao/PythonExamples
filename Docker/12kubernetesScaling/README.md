# Esempio 12 Kubernetes Scaling
Questo esempio dimostra l'utilizzo dell'**HorizontalPodAutoscaler** (HPA) di Kubernetes in due modalità:
- HPA classico con metrica CPU: una piccola immagine consuma un valore CPU parametrizzabile e modificabile a run-time
- HPA avanzato con custom metrics tramite **Prometheus** e Grafana: una piccola immagine espone un valore "numero_task" parametrizzabile e modificabile a run-time
- Una **Custom Resource Definition**, detta anche **CRD**, ti permette di estendere l'API di Kubernetes creando nuove "risorse" personalizzate, come se fossero risorse native (tipo Pod, Service, Deployment, ecc.), ma definite da te. Una volta creata una CRD, puoi usare kubectl per creare, leggere, aggiornare e cancellare oggetti di quel nuovo tipo.
    - Esempio base "messaggio"
    - Esempio "replicatore" con un controller che gestisce lo scaling di una immagine `nginx:alpine`
    - Autoscaling di una piccola applicazione "SuperCrud" con un **operator** (libreria kopf in python) *funzionante*

Facendo sempre riferimento alla [documentazione ufficiale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-cooldown-delay):
- The HorizontalPodAutoscaler is implemented as a Kubernetes API resource and a controller. The resource determines the behavior of the controller. The horizontal pod autoscaling controller, running within the Kubernetes control plane, periodically adjusts the desired scale of its target (for example, a Deployment) to match observed metrics such as average CPU utilization, average memory utilization, or any other custom metric you specify.
- Kubernetes implements horizontal pod autoscaling as a control loop that runs intermittently (it is not a continuous process).
- In Kubernetes, quando un Pod deve essere terminato (ad esempio, a causa di un aggiornamento, uno scale-down, una terminazione manuale o un fallimento del nodo), Kubernetes segue un processo di terminazione ben definito: prima di inviare il `SIGTERM` o durante il `terminationGracePeriodSeconds`, puoi specificare un `preStop hook`, questo è un comando o una richiesta HTTP che viene eseguita prima che il container venga terminato definitivamente.
- Non esiste un meccanismo diretto per "intercettare" un FailedPreStopHook e impedirgli di terminare il pod. L'obiettivo è prevenire il fallimento dell'hook attraverso una progettazione robusta e monitorare gli eventi per essere avvisati quando accade, così da poter investigare e correggere la causa radice. Concentrati sulla resilienza del tuo preStop hook e su un monitoraggio efficace.
    - Catturare il FailedPreStopHook in Kubernetes e impedire che il pod muoia è una sfida complessa, perché il fallimento di un preStop hook indica a Kubernetes che il processo di terminazione non sta andando come previsto e, per sua natura, Kubernetes procederà comunque a terminare il pod dopo il terminationGracePeriodSeconds.
    - Non puoi "catturare" il FailedPreStopHook nel senso di impedire la terminazione del pod una volta che il processo è iniziato. Il preStop hook è l'ultima possibilità del pod di eseguire un'azione prima della terminazione finale. Se fallisce, il pod morirà comunque.


Per l'esecuzione di questo esempio è indispensabile aver installato **minukube** assieme a `docker` e `kubectl`.


## Comando per l'esecuzione della versione classica
L'esempio prevede un servizio eseguito su un POD che simuli l'uso di CPU e Memoria in maniera variabile e controllabile.
- Esecuzione di minikube e configurazione del server
    ```bash
	minikube start --memory=4096 --cpus=4
	minikube addons enable metrics-server
    ```
    Verificare con freelens che il pod sia verde oppure lanciare i comandi di verifica:
    ```bash
	kubectl top nodes 
	kubectl get pods -n kube-system | grep metrics-server    
    ```
- Esecuzione dell'immagine con il `cpu.py` che simula l'uso della CPU
    ```bash
	docker build -t cpu-burner:latest .
	minikube image load cpu-burner:latest
	kubectl apply -f deploy.yaml
    ```
- Configurazione semplice dello scaling (metrica impostata al 50% della CPU)
    ```bash
    kubectl autoscale deployment cpu-burner --cpu-percent=50 --min=1 --max=5
	kubectl get hpa
	kubectl top nodes 
    kubectl describe hpa cpu-burner
    ```
- Comandi per modificare e monitorare il carico di un pod (da eseguire da dentro un POD)
    ```bash
    curl localhost:8000/change/42/33
    curl localhost:8000/top
    ```
- Rimozione di tutto
    ```bash
    kubectl delete hpa cpu-burner
    kubectl delete deployment cpu-burner
    ```

## Comando per l'esecuzione della versione con Prometheus:
L'esempio è nella sotto-cartella dedicata e tutti i comandi sono da eseguire in quella cartella. Si fa sempre riferimento alla [documentazione ufficiale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-cooldown-delay)
- Avvio ed installazione di Prometheus, vedere la [documentazione ufficiale](https://www.redhat.com/it/blog/installing-prometheus)
    ```bash
    minikube start --memory=4096 --cpus=4
    minikube addons list
    
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
    rm get_helm.sh

    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
    ```
    - Verifica dell'installazione su freelens (tutto verde nel namespace *monitoring*)
        ```bash
        kubectl get pods -n monitoring
        kubectl get svc -n monitoring

        kubectl --namespace monitoring get pods -l "release=prometheus"
        ```
    - Get Grafana 'admin' user password by running:
        ```bash
        kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
        ```
    - Per far funzionare l'esempio in locale è possibile installare Prometheus senza Heml ma è sconsigliato *e non funziona*, i passaggi sarebbero
        ```bash
        kubectl create namespace monitoring
        kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
        kubectl apply -k https://github.com/prometheus-operator/prometheus-operator/tree/main/example/prometheus-operator-crd
        minikube addons enable prometheus
        ```

- Creazione e avvio immagine che esegue il servizio di `metrics.py` e configura l'HPA
    ```bash
    docker build -t task-metrics:latest -f Dockerfile .
    minikube image load task-metrics:latest
    kubectl apply -f deployment.yaml
    kubectl apply -f serviceMonitor.yaml
    kubectl get servicemonitors -A
    ```
    - Se viene usata la versione con lo scale-down con la API `shutdown` è necessario assegnare al POD i poteri per accedere alle info di Kubernetes con il comando
        ```bash
        kubectl apply -f read-pods-rbac.yaml
        ```
    - Modifica del valore delle task-metric (da eseguire da dentro i POD)
        ```bash
        curl localhost:8000/current
        curl localhost:8000/change/80
        ```
    - In caso di modifica del Python se il servizio è già attivo, ri-eseguire il rilascio con un TAG specifico
        ```bash
        TAG=$(date +%Y%m%d%H%M%S)
        docker build -t task-metrics:$TAG .
        minikube image load task-metrics:$TAG
        echo $TAG
        kubectl set image deployment/task-metrics task-metrics=task-metrics:$TAG
        ```
        usare un tab specifico perchè a volte `latest` non funziona e non carica la nuova immagine:
        ```bash
        kubectl rollout restart deployment task-metrics
        ```
        - `kubectl set image` è il modo preferito per aggiornare un'immagine in un deployment, perché innesca automaticamente un rollout.
        - `kubectl rollout restart` è utile se vuoi forzare un riavvio dei pod senza cambiare la configurazione del deployment. Se l'immagine è già stata aggiornata (anche con lo stesso tag ma ID diverso, e la imagePullPolicy è Always), kubectl rollout restart la tirerà di nuovo.
- Verifica che Prometheus raccolga le metriche, avviare l'interfaccia grafica di Prometheus `http://localhost:9090`:
    ```bash
    kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
    ```
    e verificare:
    - status → healt → verificare che sia presente la metrica su porta 8001 e che sia verde
    - cerca numero_task nel query explorer e insere le query `numero_task` → `up{job="task-metrics"}` → `{__name__=~".*numero.*"}`
    - query da riga di comando:
        ```
        curl "http://localhost:9090/api/v1/query?query=numero_task"
        ```
- Configurazione del **prometheus-adapter** (*complicato*)
    ```bash
    helm install prometheus-adapter prometheus-community/prometheus-adapter \
    --namespace monitoring \
    --values adapter-values.yaml
    ```
    - Verifica che i dati siano correttamente caricati con il comando
        ```bash
        kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1
        ```
    - Se non compare monitorare log del pod "prometheus-adapter" in caso di errori di connessione verificare path, per esempio 
        ```bash
        kubectl run -it --rm debug --image=busybox --restart=Never -- sh
        wget -qO- http://prometheus-operated.monitoring.svc.cluster.local:9090/api/v1/query?query=up
        wget -qO- http://prometheus-prometheus-kube-prometheus-prometheus-0.prometheus-operated.monitoring.svc.cluster.local:9090/api/v1/query?query=up
        ```
        modificare il adapter-values.yaml con url funzionante
    - In caso di modifiche al adapter si può lanciare il comando di aggiornamento:
        ```bash
        helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter \
        --namespace monitoring \
        --values adapter-values.yaml
        ```
    - Verifica Prometheus e i suoi endpoint
        ```bash
        kubectl get svc -n monitoring | grep prometheus
        ```
    - Verifica log adaper (per esempio errori 404 o altri errori che Prometheus lancia silenziosamente)
        ```bash
        kubectl logs -n monitoring deployment/prometheus-adapter
        kubectl logs -n monitoring deployment/prometheus-adapter -f
        ```
- Deploy dell'HPA
    ```bash
    kubectl apply -f hpa.yaml
    kubectl get hpa
    kubectl get hpa -w
    ```
- Monitoraggio e verifica dei metriche
    ```bash
    kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/default/pods/*/custom_numero_task" | jq
    kubectl get servicemonitor -n monitoring
    ```
- Avvio UI Grafana su `http://localhost:3000`
    ```bash
    kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
    ```
    - Con utenza `admin` e password `prom-operator`
    - Verifica che Prometheus sia configurato come Data Source: su Configuration (icona ingranaggio) → Data Sources → Presenza di Prometheus, se non presente aggiungere `http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090`
    Clicca Save & Test
    - Creazione dashboard sulla metrica `numero_task`, presente anche un `grafana.json` di esempio da caricare in console

- Rimozione di tutto, *occhio che è tanta bella roba*
    ```bash
    kubectl delete -f hpa.yaml
    kubectl delete -f serviceMonitor.yaml
    kubectl delete -f deployment.yaml   
    kubectl delete -f read-pods-rbac.yaml   
    docker rmi $(docker images | grep "task-metrics" | awk '{print $3}')
    minikube image rm $(minikube image ls | grep "task-metrics" | awk '{print $1}')
    helm uninstall prometheus -n monitoring
    helm uninstall prometheus-adapter -n monitoring
    ```
- Nel file `hpa.yaml` è presente commentata la configurazione per bloccare lo scale-down, in modo che non venga mai eseguita la terminazione dei pod quando le regole di scaling lo richiederebbero, per attivarle basta sostituire lo `scaleDown` con il valore:
    ```yaml
    scaleDown:
      selectPolicy: Disabled # Questo vieta esplicitamente lo scale-down
    ```


## Custom Resource Definition CRD - Messaggio
Una CRD chiamata *messaggio* e un controller in Python usando Kopf, una libreria molto comoda per scrivere operatori Kubernetes
- file `kubectl apply -f messaggio-crd.yaml` con dentro la defizione del crd
- esecuzione della CRD con:
    ```bash
    kubectl apply -f messaggio-crd.yaml
    ```
- installazione libreria Kpof
    ```bash
    pip install kopf kubernetes
    ```
- lancio del controller
    ```bash
    kopf run messaggio-controller.py
    ```
- esecuzione della risorsa Messaggio
    ```bash
    kubectl apply -f messaggio-resouce.yaml 
    ```

- Cancellazione di tutto
    ```bash
    kubectl delete -f messaggio-resouce.yaml 
    kubectl delete -f messaggio-crd.yaml 
    ```


## Custom Resource Definition CRD - Replicatore
La risorsa CRD si chiami Replicatore, il Service creato si chiami replicatore-service, il Pod venga avviato con l’immagine Docker specificata nel campo spec.image.
Obbiettivo è creare un operator (controller) Kubernetes che gestisca un oggetto chiamato Replicatore e che:
- CRD: definisce un oggetto Replicatore con due parametri: image: immagine Docker del workload e replicas: numero di repliche da eseguire (scalabilità)
- Controller in Python (usando kopf) che: Crea un Deployment, Crea un Service dedicato (<nome>-service), Riconfigura il Deployment in base a replicas
- Dockerfile per il controller
- Manifest Kubernetes per: Deployment del controller e RBAC completo
Comandi specifici: 
- file `replicatore-crd.yaml` con la definizione della CRD "replicatore"
- file `replicatore-dockerfile` con la definizione dell'immagine "controller" (che esegue kpof come task dentro un POD)
- file `replicatore-resource.yaml` con la definizione delle regole e del deployment del Replicatore (forse meglio chiamarlo ReplicatoreCluster)
- esecuzione della CRD con:
    ```bash
    kubectl apply -f replicatore-crd.yaml
    ```
- esecuzione del controller in 
    ```bash
    docker build -t replicatore-operator -f ./replicatore-dockerfile  .
    minikube image load  replicatore-operator
    ```
- creazione del Cluster Replicatore 
    ```bash
    kubectl apply -f replicatore-resource.yaml 
    ```
- per scalare bisogna modificare il `replicatore-resource.yaml` nella configurazione *alla fine del file*:
    ```yaml
    spec:
      image: "nginx:alpine"
      replicas: 2
    ```
- cancellazione di tutto
    ```bash
    kubectl delete -f replicatore-resource.yaml
    kubectl delete -f replicatore-crd.yaml 
    ```


## Custom Resource Definition CRD - SuperCrud
*SuperCrud* è un'applicazione distribuita su Kubernetes composta da:
- Una risorsa CRD (Replicatore) che consente di specificare l'immagine e il numero di repliche iniziali.
    - file `supercrud-crd.yaml`
- Un controller (operator) basato su kopf che gestisce un oggetto personalizzato chiamato Replicatore.
    - file `supercrud-controller.py` e il `supercrud-controller-dockerfile`
- Un'applicazione web FastAPI che espone API REST CRUD con connessione a un database PostgreSQL centrale.
    - file `supercrud-applilcation.py` e il `supercrud-applilcation-dockerfile`
- Un database PostgreSQL persistente, la definizione dei permessi del controller.
    - file `supercrud-resouces.yaml`
- API del controller esposte tramite NodePort.
    - file `supercrud-resouces.yaml` nella definizione del service.
- API dell'applicazione SuperCrud esposte tramite NodePort.
    - file `supercrud-controller.py` nella defizione del servce.


Comandi per l'esecuzione dell'esempio su Minikube
- Creazione delle immagini del controller
    ```bash
    docker build -t supercrud-controller:latest -f supercrud-controller-dockerfile .
    minikube image load  supercrud-controller:latest
    ```
- Creazione delle immagini della applicazione Crud
    ```bash
    docker build -t supercrud-application:latest -f supercrud-application-dockerfile .
    minikube image load  supercrud-application:latest
    ```
- Creazione della CRD e delle risorse Kubernetes
    ```bash
    kubectl apply -f supercrud-crd.yaml 
    kubectl apply -f supercrud-resources.yaml 
    ```
    - eventuale comando di rollout per aggiornare l'operator (in caso di modifica dell'immagine senza voler ri-eseguire il deploy totale)
        ```bash
        kubectl rollout restart deployment supercrud-operator
        ```
- Eliminazione totoale 
    ```bash
    kubectl delete -f supercrud-resources.yaml 
    minikube image rm supercrud-controller:latest
    minikube image rm supercrud-application:latest
    kubectl delete -f supercrud-crd.yaml 
    ```
    - se l'operator non è riuscito ad eliminare tutto bisogna lanciare i comandi
        ```bash
        kubectl delete deployment supercrud-deployment
        kubectl delete service supercrud-service
        ```
- Comando per il test (essendo configurati come NodeGropu di minikube si usa l'ip di minikube)
    ```bash
    minikube ip
    MINI=$(minikube ip)
    echo $MINI
    curl $MINI:30080/status
    curl $MINI:30080/scale/supercrud/33
    
    for i in $(seq 12); do 
        curl $MINI:30081/
        sleep 5
    done

    curl $MINI:30080/scale/supercrud/2
    curl $MINI:30081/
    curl $MINI:30081/items
    curl -X POST $MINI:30081/items -H "Content-Type: application/json" -d '{ "name": "AlNao", "description": "Una persona magnifica." }'
    curl $MINI:30081/items
    ```
- Versione con *ingress* al posto di NodeGroup
    - installazione addons 
        ```bash
        minikube addons enable ingress
        ```
    - nel file `supercrud-resources.yaml` è presente il componente commentato *non funzionante*




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

