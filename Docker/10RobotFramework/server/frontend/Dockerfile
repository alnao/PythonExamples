FROM python:3.9-slim

RUN apt-get update && apt-get install -y iputils-ping curl unzip
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install
RUN export AWS_ACCESS_KEY_ID="fakeAccessKey"
RUN export AWS_SECRET_ACCESS_KEY="fakeSecretKey"
RUN export AWS_DEFAULT_REGION="us-east-1"
RUN export AWS_PAGER=""

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]