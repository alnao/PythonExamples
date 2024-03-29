# Docker esempio 02 flask example
Sempice applicazione flask (web e API) che viene seguita dentro ad un docker 


Riferimenti di esempio:
- https://www.freecodecamp.org/news/how-to-dockerize-a-flask-app/
- https://www.digitalocean.com/community/tutorials/how-to-build-and-deploy-a-flask-application-using-docker-on-ubuntu-20-04
- https://medium.com/geekculture/how-to-dockerize-your-flask-application-2d0487ecefb8

Nota: è necessario il host nel comando  app.run(host="0.0.0.0", port=5000, debug=True)


# Comandi per la creazione l'esecuzione in sistema locale 
```
$ docker build . -t flask-login
$ docker run -it --rm -d -p 5001:5001 flask-login 
$ docker ps --latest
$ docker stop $(docker ps -q)
$ docker rm $(docker ps -a -q)
```


Per eseguire bash dentro alla immagine in esecuzione
```
$ docker exec -t -i $(docker ps -q) /bin/bash
```


Altri comandi specifici:
- https://www.docker.com/blog/how-to-use-the-official-nginx-docker-image/
    - docker run -it --rm -d -p 8087:80 --name web nginx
-  https://www.baeldung.com/ops/assign-port-docker-container
    - docker run -d -p 5001:80 --name httpd-container httpd


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [alnao.it](https://www.alnao.it/).


## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*