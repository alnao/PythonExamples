from fastapi import FastAPI
from prometheus_client import start_http_server, Gauge
import socket
import threading
import time
import uvicorn
import requests
from kubernetes import client, config
import os
import logging

app = FastAPI()

MAX_TASK_PER_POD = int(os.environ.get("MAX_TASK_PER_POD", "50"))
NAMESPACE = os.environ.get("POD_NAMESPACE", "default")
LABEL_SELECTOR = os.environ.get("LABEL_SELECTOR" , "app=task-metrics")

pod_name = socket.gethostname()
numero_task_gauge = Gauge("numero_task", "Numero di task attivi", ["pod"])
task_count = {"value": 1}

# Ottieni un logger per la tua applicazione
logger = logging.getLogger(__name__)
# Configura il livello di logging (opzionale, Uvicorn lo sovrascrive a seconda del suo --log-level)
logging.basicConfig(level=logging.INFO)

def metrics_server():
    logger.info("Start metrics_server")
    start_http_server(8001)
    while True:
        numero_task_gauge.labels(pod=pod_name).set(task_count["value"])
        time.sleep(5)

@app.get("/change/{new_value}")
def change_task_count(new_value: int):
    logger.info("change " + str(new_value))
    task_count["value"] = max(0, min(new_value, 100))
    return {"numero_task": task_count["value"]}

@app.get("/current")
def current():
    logger.info("current " + str(task_count["value"]))
    return {"numero_task": task_count["value"]}

@app.get("/shutdown")
def shutdown():
    logger.info("shutdown")
    # Inizializza client Kubernetes (in cluster)
    config.load_incluster_config()
    v1 = client.CoreV1Api()

    # Lista dei pod nello stesso namespace con stessa label (es: app=task-app)
    pods = v1.list_namespaced_pod(namespace=NAMESPACE, label_selector=LABEL_SELECTOR)

    # Ordina i pod in base al creationTimestamp
    # Convertiamo la stringa creationTimestamp in un oggetto datetime per un confronto corretto
    sorted_pods = sorted(
        pods.items,
        key=lambda pod: pod.metadata.creation_timestamp
    )

    my_tasks = task_count["value"]
    redistribuiti = 0

    for pod in sorted_pods: #ex pods.items:
        other_pod_name = pod.metadata.name
        logger.info("pod=" + other_pod_name)
        if other_pod_name == pod_name or redistribuiti >= my_tasks:
            continue

        pod_ip = pod.status.pod_ip
        try:
            res = requests.get(f"http://{pod_ip}:8000/current", timeout=1)
            other_tasks = res.json().get("numero_task", 0)

            spazio_disponibile = MAX_TASK_PER_POD - other_tasks
            logger.info("pod=" + other_pod_name + " numero_task=" + str(other_tasks) + " spazio_disponibile="+str(spazio_disponibile))
            if spazio_disponibile <= 0:
                continue

            da_trasferire = min(spazio_disponibile, my_tasks - redistribuiti)
            new_value = other_tasks + da_trasferire
            logger.info("pod=" + other_pod_name + " da_trasferire=" +str(da_trasferire) + " new_value=" + str(new_value))
            requests.get(f"http://{pod_ip}:8000/change/{new_value}", timeout=1)

            logger.info("pod=" + other_pod_name + " new_value=" + str(new_value))
            redistribuiti += da_trasferire
            logger.info("redistribuiti=" + str(redistribuiti))

        except Exception as e:
            print(f"Errore nel contattare il pod {other_pod_name}: {e}")

    task_count["value"] = my_tasks - redistribuiti
    return {
        "messaggio": "Shutdown con ridistribuzione",
        "task_redistribuiti": redistribuiti,
        "task_residui": task_count["value"]
    }

if __name__ == "__main__":
    print("v11luglio1146")
    threading.Thread(target=metrics_server, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
