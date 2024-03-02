#HOW run Flask on Docker 
#see https://www.freecodecamp.org/news/how-to-dockerize-a-flask-app/
#ßee https://www.digitalocean.com/community/tutorials/how-to-build-and-deploy-a-flask-application-using-docker-on-ubuntu-20-04
#nota: è necessario il host nel comando  app.run(host="0.0.0.0", port=5000, debug=True)
#ßee https://medium.com/geekculture/how-to-dockerize-your-flask-application-2d0487ecefb8

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

# commands to create and run a image in local machine:
#    $ docker build . -t flask-login
#    $ docker run -it --rm -d -p 5001:5001 flask-login 
#    $ docker ps --latest
#       nota: bash into docker
#           $ docker exec -t -i $(docker ps -q) /bin/bash
#    $ docker stop $(docker ps -q)
#    $ docker rm $(docker ps -a -q)

# altri esempi di docker web per esempio
# https://www.docker.com/blog/how-to-use-the-official-nginx-docker-image/
# docker run -it --rm -d -p 8087:80 --name web nginx
# https://www.baeldung.com/ops/assign-port-docker-container
# docker run -d -p 5001:80 --name httpd-container httpd