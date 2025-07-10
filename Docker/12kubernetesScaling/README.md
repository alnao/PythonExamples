# Esempio 12 Kubernetes Scaling
Questo esempio dimostra l'utilizzo dell'**HorizontalPodAutoscaler** (HPA) di Kubernetes in due modalità:
- HPA classico con metrica CPU
- HPA avanzato con custom metrics tramite **Prometheus** e Grafana


Facendo sempre riferimento alla [documentazione ufficiale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-cooldown-delay):
- The HorizontalPodAutoscaler is implemented as a Kubernetes API resource and a controller. The resource determines the behavior of the controller. The horizontal pod autoscaling controller, running within the Kubernetes control plane, periodically adjusts the desired scale of its target (for example, a Deployment) to match observed metrics such as average CPU utilization, average memory utilization, or any other custom metric you specify.
- Kubernetes implements horizontal pod autoscaling as a control loop that runs intermittently (it is not a continuous process).


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
    #NON SO kubectl create namespace monitoring
    #NON SO kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
    #NON SO kubectl apply -k https://github.com/prometheus-operator/prometheus-operator/tree/main/example/prometheus-operator-crd
    #NON SO minikube addons enable prometheus
    
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
    Verifica dell'installazione su freelens (tutto verde nel namespace *monitoring*)
    ```
    kubectl get pods -n monitoring
    kubectl get svc -n monitoring

    kubectl --namespace monitoring get pods -l "release=prometheus"
    ```
    Get Grafana 'admin' user password by running:
    ```
    kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
    ```

- Creazione e avvio immagine che esegue il servizio di `metrics.py` e configura l'HPA
    ```
    docker build -t task-metrics:latest -f Dockerfile .
    minikube image load task-metrics:latest
    kubectl apply -f deployment.yaml
    kubectl apply -f serviceMonitor.yaml
    kubectl get servicemonitors -A
    ```
    - Modifica del valore delle task-metric (da eseguire da dentro i POD)
        ```
        curl localhost:8000/current
        curl localhost:8000/change/80
        ```
    - In caso di modifica del Python, per ri-eseguire il rilascio
        ```
        docker build -t task-metrics:latest .
        minikube image load task-metrics:latest
        kubectl rollout restart deployment task-metrics
        ```

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

- Rimozione di tutto (tanta bella roba)
    ```
    helm uninstall prometheus-adapter -n monitoring
    kubectl delete -f hpa.yaml
    kubectl delete -f serviceMonitor.yaml
    kubectl delete -f deployment.yaml   
    minikube image rm task-metrics:latest
    helm uninstall prometheus -n monitoring
    ```
- Nota: per le logiche di *scale-down*, nel `hpa.yaml` è configurata la logica di down in modo che non venga mai eseguito:
    ```
    scaleDown:
      selectPolicy: Disabled # Questo vieta esplicitamente lo scale-down
    ```
    oppure è possibile attivare una regola di scale down specifica come presente come commento nel file.


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*








