# Docker esempio 01 simple panda
Sempice codice python che viene seguito dentro ad un docker 

Riferimento https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

# Comandi per la creazione l'esecuzione in sistema locale 
```
$ docker builds -t sample-aws-code .
$ docker run sample-aws-code
$ docker ps --latest
```

# Comandi per caricare in AWS-ECR 
Riferimento https://medium.com/codex/run-a-python-code-on-aws-batch-part-2-uploading-data-to-ecr-and-creation-of-computing-c5dab12cd3eb
```
$ aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com
$ docker build -t nome-ecs-repo-uno .
$ docker tag nome-ecs-repo-uno:latest xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
$ docker push xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
```

# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [alnao.it](https://www.alnao.it/).


## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*