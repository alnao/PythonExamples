FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y gcc python3-dev curl wget gcc python3-dev procps nmon htop glances && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY metrics.py .

RUN pip install fastapi uvicorn prometheus_client kubernetes

EXPOSE 8000
EXPOSE 8001

CMD ["python", "metrics.py"]
