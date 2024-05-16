FROM python:3.8
RUN  apt-get update
RUN  apt-get -y install libxml2-dev libxmlsec1-dev libxmlsec1-openssl
WORKDIR /project
ADD . /project
RUN pip install -r requirements.txt
CMD ["python","main.py"]

