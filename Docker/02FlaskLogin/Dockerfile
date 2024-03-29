FROM python:3.8

WORKDIR /python-docker
ADD ./app.py .
ADD ./users.db .
ADD ./requirements.txt .
COPY ./templates/ ./templates/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
#RUN pip install flask 
#RUN pip install pysqlite3-binary

CMD ["python","./app.py"]
#CMD [ "python3", "-m" , "flask", "run", "-p 5001"]
