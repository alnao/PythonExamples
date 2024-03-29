# Docker esempio 03 api persone senza DB anche su ECS
Sempice codice python che viene seguito dentro ad un docker 

Riferimento https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

# Comandi per la creazione l'esecuzione in sistema locale 
```
$ docker build . -t api-persone-nodb
$ docker run -it --rm -d -p 5001:5001 api-persone-nodb
$ docker ps --latest
$ docker stop $(docker ps -q)
$ docker rm $(docker ps -a -q)
```


To test:
```
# curl  localhost:5001/persone
# curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST localhost:5001/persone
```


# Comandi per caricare in AWS-ECR 
Riferimento https://medium.com/codex/run-a-python-code-on-aws-batch-part-2-uploading-data-to-ecr-and-creation-of-computing-c5dab12cd3eb
```
$ aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com
$ docker build -t nome-ecs-repo-uno .
$ docker tag nome-ecs-repo-uno:latest xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
$ docker push xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
```

# Comandi per eseguire in AWS-ECS
```
$ aws ecs register-task-definition --cli-input-json file://taskECS.json
$ aws ecs run-task --cluster docker-cluster --task-definition api-persone-nodb:2 --count 1
$ aws ecs list-tasks --cluster docker-cluster 
```


To test:
```
$ curl  3.253.67.174:5001/persone
$ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST 3.253.67.174:5001/persone
$ aws ecs stop-task --cluster docker-cluster --task xxxx
```

## ECS Multiple tasks with different ports (bridge system)
Riferimento bridge network in https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#network_mode
```
$ aws ecs register-task-definition --cli-input-json file://taskECSbridge.json
$ aws ecs run-task --cluster docker-cluster --task-definition api-persone-nodb:3 --count 1
$ aws ecs list-tasks --cluster docker-cluster 
$ curl  3.253.67.174:32770/persone
$ curl  3.253.67.174:32769/persone
$ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST 3.253.67.174:32770/persone
$ curl  3.253.67.174:32770/persone
$ curl  3.253.67.174:32769/persone
$ aws ecs stop-task --cluster docker-cluster --task 52020c440cf64088b946c2f80ff26514
$ aws ecs stop-task --cluster docker-cluster --task 6f4d3e6ff1d743b7b4c814fc68e2c411
$ aws ecs stop-task --cluster docker-cluster --task 8493986540274fb7a803a30482b7a9c9
```

# Comandi per eseguire in AWS-ECS con Fargate
```
$ aws ecs create-cluster --cluster-name fargate-cluster
```
Verificare regola IAM con AmazonEC2ContainerRegistryFullAccess, AmazonECS_FullAccess, AmazonSSMManagedInstanceCore	
```
       trust with {"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"},"Action": "sts:AssumeRole"}
```
Riferimenti https://docs.aws.amazon.com/AmazonECS/latest/developerguide/example_task_definitions.html


```
$	aws ecs register-task-definition --cli-input-json file://taskECSwithFargate.json
$	aws ecs list-task-definitions
$ 	aws ecs create-service --cluster fargate-cluster --service-name fargate-service --task-definition api-persone-nodb-farg:1 --desired-count 1 --launch-type "FARGATE" --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}" --enable-execute-command
$ 	aws ecs list-services --cluster fargate-cluster
$	aws ecs describe-services --cluster fargate-cluster --services fargate-service
$	aws ecs list-tasks --cluster fargate-cluster --service fargate-service
$	aws ecs describe-tasks --cluster fargate-cluster --tasks arn:aws:ecs:eu-west-1:xxxxxx:task/fargate-cluster/d7f4c21df95a4d6b8c04e29119d87e6c
$	aws ec2 describe-network-interfaces --network-interface-id eni-029e3d81b30cd9da2
    check ip in console 
```


Per eseguire comandi 
riferimento https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-windows.html
```
$ aws ecs execute-command --cluster fargate-cluster  --task arn:aws:ecs:eu-west-1:xxxxxx:task/fargate-cluster/d7f4c21df95a4d6b8c04e29119d87e6c --container  fargate-app --interactive --command "ls"
$ aws ecs delete-service --cluster fargate-cluster --service fargate-service --force
```


To test:
```
$	curl  <publicIp>:5001/persone
$	curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST <publicIp>:5001/persone
$	curl  <publicIp>:5001/persone
```


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [alnao.it](https://www.alnao.it/).


## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*