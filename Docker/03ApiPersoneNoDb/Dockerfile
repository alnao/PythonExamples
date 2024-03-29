#API rest with Flask on Docker 

FROM python:3.8

WORKDIR /usr/src/app
ADD ./app.py .
ADD ./requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 5001
CMD ["python","./app.py"]
#CMD [ "python3", "-m" , "flask", "run", "-p 5001"]


