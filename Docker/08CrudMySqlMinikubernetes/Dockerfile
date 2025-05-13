
FROM python:3.10-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install -r requirements.txt
RUN apt update && apt install -y wget
RUN apt update && apt install -y curl
    #curl kubernetes.default:3306
RUN apt update && apt install -y iputils-ping
    #ping py-esempio08-mysql-svc.default.svc.cluster.local
RUN apt update && apt install -y dnsutils  
    #nslookup py-esempio08-mysql-svc.default.svc.cluster.local
    #nslookup kubernetes.default
RUN apt update && apt install -y netcat
RUN apt update && apt install -y telnet
#RUN apt update && apt install -y mysql-client

COPY app/ .
EXPOSE 5000
CMD ["python", "app.py"]


#docker build -t alnao/flask-mysql-demo:1.0 .

