# Esempio 12 Kubernetes Scaling
Questo esempio dimostra l'utilizzo dell'**HorizontalPodAutoscaler** (HPA) di Kubernetes in due modalità:
- HPA classico con metrica CPU: una piccola immagine consuma un valore CPU parametrizzabile e modificabile a run-time
- HPA avanzato con custom metrics tramite **Prometheus** e Grafana: una piccola immagine espone un valore "numero_task" parametrizzabile e modificabile a run-time


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
    ```
	minikube start --memory=4096 --cpus=4
	minikube addons enable metrics-server
    ```
    Verificare con freelens che il pod sia verde oppure lanciare i comandi di verifica:
    ```
	kubectl top nodes 
	kubectl get pods -n kube-system | grep metrics-server    
    ```
- Esecuzione dell'immagine con il `cpu.py` che simula l'uso della CPU
    ```
	docker build -t cpu-burner:latest .
	minikube image load cpu-burner:latest
	kubectl apply -f deploy.yaml
    ```
- Configurazione semplice dello scaling (metrica impostata al 50% della CPU)
    ```
    kubectl autoscale deployment cpu-burner --cpu-percent=50 --min=1 --max=5
	kubectl get hpa
	kubectl top nodes 
    kubectl describe hpa cpu-burner
    ```
- Comandi per modificare e monitorare il carico di un pod (da eseguire da dentro un POD)
    ```
    curl localhost:8000/change/42/33
    curl localhost:8000/top
    ```
- Rimozione di tutto
    ```
    kubectl delete hpa cpu-burner
    kubectl delete deployment cpu-burner
    ```

## Comando per l'esecuzione della versione con Prometheus:
L'esempio è nella sotto-cartella dedicata e tutti i comandi sono da eseguire in quella cartella. Si fa sempre riferimento alla [documentazione ufficiale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-cooldown-delay)
- Avvio ed installazione di Prometheus, vedere la [documentazione ufficiale](https://www.redhat.com/it/blog/installing-prometheus)
    ```
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
        ```
        kubectl get pods -n monitoring
        kubectl get svc -n monitoring

        kubectl --namespace monitoring get pods -l "release=prometheus"
        ```
    - Get Grafana 'admin' user password by running:
        ```
        kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
        ```
    - Per far funzionare l'esempio in locale è possibile installare Prometheus senza Heml ma è sconsigliato *e non funziona*, i passaggi sarebbero
        ```
        kubectl create namespace monitoring
        kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
        kubectl apply -k https://github.com/prometheus-operator/prometheus-operator/tree/main/example/prometheus-operator-crd
        minikube addons enable prometheus
        ```

- Creazione e avvio immagine che esegue il servizio di `metrics.py` e configura l'HPA
    ```
    docker build -t task-metrics:latest -f Dockerfile .
    minikube image load task-metrics:latest
    kubectl apply -f deployment.yaml
    kubectl apply -f serviceMonitor.yaml
    kubectl get servicemonitors -A
    ```
    - Se viene usata la versione con lo scale-down con la API `shutdown` è necessario assegnare al POD i poteri per accedere alle info di Kubernetes con il comando
        ```
        kubectl apply -f read-pods-rbac.yaml
        ```
    - Modifica del valore delle task-metric (da eseguire da dentro i POD)
        ```
        curl localhost:8000/current
        curl localhost:8000/change/80
        ```
    - In caso di modifica del Python se il servizio è già attivo, ri-eseguire il rilascio con un TAG specifico
        ```
        TAG=$(date +%Y%m%d%H%M%S)
        docker build -t task-metrics:$TAG .
        minikube image load task-metrics:$TAG
        echo $TAG
        kubectl set image deployment/task-metrics task-metrics=task-metrics:$TAG
        ```
        usare un tab specifico perchè a volte `latest` non funziona e non carica la nuova immagine:
        ```
        kubectl rollout restart deployment task-metrics
        ```
        - `kubectl set image` è il modo preferito per aggiornare un'immagine in un deployment, perché innesca automaticamente un rollout.
        - `kubectl rollout restart` è utile se vuoi forzare un riavvio dei pod senza cambiare la configurazione del deployment. Se l'immagine è già stata aggiornata (anche con lo stesso tag ma ID diverso, e la imagePullPolicy è Always), kubectl rollout restart la tirerà di nuovo.
- Verifica che Prometheus raccolga le metriche, avviare l'interfaccia grafica di Prometheus `http://localhost:9090`:
    ```
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
    ```
    helm install prometheus-adapter prometheus-community/prometheus-adapter \
    --namespace monitoring \
    --values adapter-values.yaml
    ```
    - Verifica che i dati siano correttamente caricati con il comando
        ```
        kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1
        ```
    - Se non compare monitorare log del pod "prometheus-adapter" in caso di errori di connessione verificare path, per esempio 
        ```
        kubectl run -it --rm debug --image=busybox --restart=Never -- sh
        wget -qO- http://prometheus-operated.monitoring.svc.cluster.local:9090/api/v1/query?query=up
        wget -qO- http://prometheus-prometheus-kube-prometheus-prometheus-0.prometheus-operated.monitoring.svc.cluster.local:9090/api/v1/query?query=up
        ```
        modificare il adapter-values.yaml con url funzionante
    - In caso di modifiche al adapter si può lanciare il comando di aggiornamento:
        ```
        helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter \
        --namespace monitoring \
        --values adapter-values.yaml
        ```
    - Verifica Prometheus e i suoi endpoint
        ```
        kubectl get svc -n monitoring | grep prometheus
        ```
    - Verifica log adaper (per esempio errori 404 o altri errori che Prometheus lancia silenziosamente)
        ```
        kubectl logs -n monitoring deployment/prometheus-adapter
        kubectl logs -n monitoring deployment/prometheus-adapter -f
        ```
- Deploy dell'HPA
    ```
    kubectl apply -f hpa.yaml
    kubectl get hpa
    kubectl get hpa -w
    ```
- Monitoraggio e verifica dei metriche
    ```    
    kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/default/pods/*/custom_numero_task" | jq
    kubectl get servicemonitor -n monitoring
    ```
- Avvio UI Grafana su `http://localhost:3000`
    ```
    kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
    ```
    - Con utenza `admin` e password `prom-operator`
    - Verifica che Prometheus sia configurato come Data Source: su Configuration (icona ingranaggio) → Data Sources → Presenza di Prometheus, se non presente aggiungere `http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090`
    Clicca Save & Test
    - Creazione dashboard sulla metrica `numero_task`, presente anche un `grafana.json` di esempio da caricare in console

- Rimozione di tutto, *occhio che è tanta bella roba*
    ```
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
    ```
    scaleDown:
      selectPolicy: Disabled # Questo vieta esplicitamente lo scale-down
    ```
    


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*








