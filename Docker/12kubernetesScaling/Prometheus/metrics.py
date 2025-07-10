from fastapi import FastAPI
from prometheus_client import start_http_server, Gauge
import socket
import threading
import time
import uvicorn

app = FastAPI()

pod_name = socket.gethostname()
numero_task_gauge = Gauge("numero_task", "Numero di task attivi", ["pod"])
task_count = {"value": 10}

def metrics_server():
    start_http_server(8001)
    while True:
        numero_task_gauge.labels(pod=pod_name).set(task_count["value"])
        time.sleep(5)

@app.get("/change/{new_value}")
def change_task_count(new_value: int):
    task_count["value"] = max(0, min(new_value, 100))
    return {"numero_task": task_count["value"]}

@app.get("/current")
def current():
    return {"numero_task": task_count["value"]}

if __name__ == "__main__":
    print("V10lug0923")
    threading.Thread(target=metrics_server, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
