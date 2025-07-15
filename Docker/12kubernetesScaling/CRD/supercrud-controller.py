import kopf
import kubernetes
from fastapi import FastAPI
import uvicorn
import asyncio
import threading
import os
import logging

app = FastAPI()
supercrud_data = {}  # Stato interno

# Carica la configurazione del cluster
kubernetes.config.load_incluster_config()
api = kubernetes.client.AppsV1Api()
core = kubernetes.client.CoreV1Api()

# Ottieni un logger per la tua applicazione
logger = logging.getLogger(__name__)
# Configura il livello di logging (opzionale, Uvicorn lo sovrascrive a seconda del suo --log-level)
logging.basicConfig(level=logging.INFO)

# Kopf: Crea Deployment e Service
@kopf.on.create('example.alnao.it', 'v1', 'supercruds')
@kopf.on.update('example.alnao.it', 'v1', 'supercruds')
def create_fn(spec, name, namespace, logger, **kwargs):
    logger.info(f"Avviato create_fn {name} {namespace}")
    image = spec.get('image')
    replicas = spec.get('replicas', 1)

    supercrud_data[name] = {'namespace': namespace}

    # Deployment
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": f"{name}-deployment"},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name}},
                "spec": {
                    "containers": [{
                        "name": name,
                        "image": image,
                        "imagePullPolicy": "Never",
                        "ports": [{"containerPort": 8000}],
                        "env": [
                            {"name": "DB_HOST", "value": "postgres-service"},
                            {"name": "DB_PORT", "value": "5432"},
                            {"name": "DB_NAME", "value": "mydb"},
                            {"name": "DB_USER", "value": "admin"},
                            {"name": "DB_PASSWORD", "value": "secret"}
                        ]
                    }]
                }
            }
        }
    }
    
    try:
        # Prova a creare il deployment
        api.create_namespaced_deployment(namespace, deployment)
        logger.info(f"Deployment '{name}-deployment' creato")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:  # Conflict - già esistente
            # Aggiorna il deployment esistente
            api.patch_namespaced_deployment(name=f"{name}-deployment", namespace=namespace, body=deployment)
            logger.info(f"Deployment '{name}-deployment' aggiornato")
        else:
            raise

    # Service
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": f"{name}-service"},
        "spec": {
            "selector": {"app": name},
            "type": "NodePort", #nota : il nodePort serve per esporre verso esterno, alternativa al "type": "LoadBalancer", 
            "ports": [{"port": 80, "targetPort": 8000, "nodePort": 30081}]
        }
    }
    
    try:
        core.create_namespaced_service(namespace, service)
        logger.info(f"Service '{name}-service' creato")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 409:  # Conflict - già esistente
            core.patch_namespaced_service(name=f"{name}-service", namespace=namespace, body=service)
            logger.info(f"Service '{name}-service' aggiornato")
        else:
            raise

    logger.info(f"supercrud '{name}' creato con {replicas} repliche.")


# Gestione della cancellazione
@kopf.on.delete('example.alnao.it', 'v1', 'supercruds')
def delete_fn(name, namespace, logger, **kwargs):
    logger.info(f"Avviato delete_fn {name} {namespace}")
    try:
        # Elimina il deployment
        api.delete_namespaced_deployment(name=f"{name}-deployment", namespace=namespace)
        logger.info(f"Deployment '{name}-deployment' eliminato")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status != 404:  # Ignora se non trovato
            logger.error(f"Errore eliminando deployment: {e}")
    
    try:
        # Elimina il service
        core.delete_namespaced_service(name=f"{name}-service", namespace=namespace)
        logger.info(f"Service '{name}-service' eliminato")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status != 404:  # Ignora se non trovato
            logger.error(f"Errore eliminando service: {e}")
    
    # Rimuovi dallo stato interno
    if name in supercrud_data:
        del supercrud_data[name]
    
    logger.info(f"supercrud '{name}' eliminato.")


# FastAPI: API per scalare un supercrud
@app.get("/scale/{name}/{replicas}")
async def scale_supercrud(name: str, replicas: int):
    logger.info(f"Avviato scale_supercrud {name} {replicas}")
    if name not in supercrud_data:
        return {"error": "supercrud not found"}
    namespace = supercrud_data[name]['namespace']
    deployment_name = f"{name}-deployment"

    body = {"spec": {"replicas": replicas}}
    try:
        api.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=body)
        return {"status": "updated", "name": name, "replicas": replicas}
    except kubernetes.client.exceptions.ApiException as e:
        return {"error": f"Failed to scale: {e}"}


# API per ottenere lo stato dei supercruds
@app.get("/status")
async def get_status():
    return {"supercruds": supercrud_data}


# API per ottenere informazioni su un supercrud specifico
@app.get("/status/{name}")
async def get_supercrud_status(name: str):
    logger.info(f"Avviato get_supercrud_status {name}")
    if name not in supercrud_data:
        return {"error": "supercrud not found"}
    
    namespace = supercrud_data[name]['namespace']
    deployment_name = f"{name}-deployment"
    
    try:
        deployment = api.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        return {
            "name": name,
            "namespace": namespace,
            "replicas": deployment.spec.replicas,
            "ready_replicas": deployment.status.ready_replicas or 0,
            "available_replicas": deployment.status.available_replicas or 0
        }
    except kubernetes.client.exceptions.ApiException as e:
        return {"error": f"Failed to get status: {e}"}


def run_kopf():
    logger.info(f"Avviato run_kopf")
    kopf.configure(verbose=True)
    asyncio.run(kopf.operator())


def run_fastapi():
    logger.info(f"Avviato run_fastapi")
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def main():
    logger.info(f"Avvia Kopf e FastAPI in thread separati")
    # Thread per Kopf
    kopf_thread = threading.Thread(target=run_kopf, daemon=True)
    kopf_thread.start()
    
    # Thread per FastAPI (questo diventa il thread principale)
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()
    
    # Aspetta che i thread terminino
    logger.info(f"Avviati, ora mi metto in attesa che entrambi terminino")
    kopf_thread.join()
    fastapi_thread.join()


if __name__ == "__main__":
    main()