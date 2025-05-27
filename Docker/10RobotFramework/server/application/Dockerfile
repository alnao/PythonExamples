# Utilizza un'immagine base ufficiale di Python
FROM python:3.9-slim


RUN apt-get update && apt-get install -y iputils-ping curl unzip
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install
RUN export AWS_ACCESS_KEY_ID="fakeAccessKey"
RUN export AWS_SECRET_ACCESS_KEY="fakeSecretKey"
RUN export AWS_DEFAULT_REGION="us-east-1"
RUN export AWS_PAGER=""
# RUN aws dynamodb list-tables --endpoint-url http://dynamodb-local:8000 --region us-east-1
# RUN aws dynamodb scan --table-name alberto-dy2  --endpoint-url http://dynamodb-local:8000 --region us-east-1 

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia i file necessari nel container
COPY requirements.txt .
COPY kafka_consumer.py .

# Installa le dipendenze
#RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Esegui il programma quando si avvia il container
CMD ["python", "kafka_consumer.py"]



# docker build -t kafka-consumer-app .
# docker run \
#   -e KAFKA_BOOTSTRAP_SERVERS="kafka:9092" \
#   -e DYNAMODB_ENDPOINT="http://dynamodb-local:8000" \
#   -e MAX_WORKERS=1 \
#   --network host \
#   kafka-consumer-app
