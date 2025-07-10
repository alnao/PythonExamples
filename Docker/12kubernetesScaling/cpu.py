import time
import threading
import multiprocessing
import psutil
from fastapi import FastAPI
import uvicorn

app = FastAPI()

cpu_target = multiprocessing.Value("i", 1)  # Da 1 a 100
mem_target = multiprocessing.Value("d", 0.0)

def cpu_task():
    print("Start cpu_task")
    period = 0.1  # 100ms ciclo
    busy = period * 0.01  # ~1% load
    idle = period - busy

    end_time = time.time() + 60  # durata del task: 60s
    while time.time() < end_time:
        start = time.time()
        while (time.time() - start) < busy:
            pass  # carico CPU
        time.sleep(idle)
    

def memory_load(mem_percent):
    print("Start mem_percent " + str(mem_percent) )
    total = psutil.virtual_memory().total
    target_bytes = int(total * mem_percent / 100)
    block_size = 10 * 1024 * 1024  # 10 MB
    allocated = []
    try:
        while sum(len(b) for b in allocated) < target_bytes:
            to_allocate = min(block_size, target_bytes - sum(len(b) for b in allocated))
            allocated.append(bytearray(to_allocate))
            time.sleep(0.05)
        time.sleep(60)  # tieni in memoria per 60s
    except MemoryError:
        pass

def run_load():
    while True:
        cpu_tasks = max(1, min(cpu_target.value, 100))
        print(f"Spawning {cpu_tasks} CPU tasks")
        processes = []

        for _ in range(cpu_tasks):
            p = multiprocessing.Process(target=cpu_task)
            p.start()
            processes.append(p)

        mem_proc = multiprocessing.Process(target=memory_load, args=(mem_target.value,))
        mem_proc.start()
        processes.append(mem_proc)

        for p in processes:
            p.join()

@app.get("/change/{cpu}/{mem}")
def change(cpu: int, mem: float):
    cpu_target.value = max(1, min(cpu, 100))
    mem_target.value = max(0, min(mem, 100))
    return {"cpu_tasks": cpu_target.value, "mem_target_percent": mem_target.value}

@app.get("/top")
def top_status():
    process = psutil.Process()
    mem = psutil.virtual_memory()

    return {
        "system_cpu_percent": psutil.cpu_percent(interval=0.2),
        "system_memory": {
            "total_mb": round(mem.total / (1024 * 1024), 2),
            "used_mb": round(mem.used / (1024 * 1024), 2),
            "available_mb": round(mem.available / (1024 * 1024), 2),
            "percent_used": mem.percent
        },
        "current_process": {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(interval=0.2),
            "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
            "memory_percent": process.memory_percent()
        }
    }

def main():
    cpu_target.value = 1
    mem_target.value = 0.0
    print(f"Initial CPU tasks: {cpu_target.value}, MEM target: {mem_target.value}%")
    threading.Thread(target=run_load, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("Starting CPU burner v1146")
    main()
