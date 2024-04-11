FROM python:3.8
WORKDIR /project
ADD . /project
RUN pip install -r requirements.txt
CMD ["python","app.py"]

#docker build . -t flask-login-ex
#docker run -it --rm -d -p 8001:8001 flask-login-ex
#
#docker logs --follow a10deacbb9c4
#
#docker stop a10deacbb9c4
