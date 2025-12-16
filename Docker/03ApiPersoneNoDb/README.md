# Docker esempio 03 api persone senza DB anche su ECS
Sempice codice python che viene seguito dentro ad un docker 

Riferimento https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

# Comandi per la creazione l'esecuzione in sistema locale 
```bash
$ docker build . -t api-persone-nodb
$ docker run -it --rm -d -p 5001:5001 api-persone-nodb
$ docker ps --latest
$ docker stop $(docker ps -q)
$ docker rm $(docker ps -a -q)
```


To test:
```bash
$ curl  localhost:5001/persone
$ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST localhost:5001/persone
```


# Comandi per caricare in AWS-ECR 
Riferimento https://medium.com/codex/run-a-python-code-on-aws-batch-part-2-uploading-data-to-ecr-and-creation-of-computing-c5dab12cd3eb
```bash
$ aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com
$ docker build -t nome-ecs-repo-uno .
$ docker tag nome-ecs-repo-uno:latest xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
$ docker push xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
```

# Comandi per eseguire in AWS-ECS
```bash
$ aws ecs register-task-definition --cli-input-json file://taskECS.json
$ aws ecs run-task --cluster docker-cluster --task-definition api-persone-nodb:2 --count 1
$ aws ecs list-tasks --cluster docker-cluster 
```


To test:
```bash
$ curl  <PUBLIC_IP>:5001/persone
$ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST <PUBLIC_IP>:5001/persone
$ aws ecs stop-task --cluster docker-cluster --task xxxx
```

## ECS Multiple tasks with different ports (bridge system)
Riferimento bridge network in https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#network_mode
```bash
$ aws ecs register-task-definition --cli-input-json file://taskECSbridge.json
$ aws ecs run-task --cluster docker-cluster --task-definition api-persone-nodb:3 --count 1
$ aws ecs list-tasks --cluster docker-cluster 
$ curl  <PUBLIC_IP>:32770/persone
$ curl  <PUBLIC_IP>:32769/persone
$ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST <PUBLIC_IP>:32770/persone
$ curl  <PUBLIC_IP>:32770/persone
$ curl  <PUBLIC_IP>:32769/persone
$ aws ecs stop-task --cluster docker-cluster --task 52020c440cf64088b946c2f80ff26514
$ aws ecs stop-task --cluster docker-cluster --task 6f4d3e6ff1d743b7b4c814fc68e2c411
$ aws ecs stop-task --cluster docker-cluster --task 8493986540274fb7a803a30482b7a9c9
```

# Comandi per eseguire in AWS-ECS con Fargate
```bash
$ aws ecs create-cluster --cluster-name fargate-cluster
```
Verificare regola IAM con AmazonEC2ContainerRegistryFullAccess, AmazonECS_FullAccess, AmazonSSMManagedInstanceCore	
```
trust with {"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"},"Action": "sts:AssumeRole"}
```
Riferimenti https://docs.aws.amazon.com/AmazonECS/latest/developerguide/example_task_definitions.html

```bash
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
```bash
$ aws ecs execute-command --cluster fargate-cluster  --task arn:aws:ecs:eu-west-1:xxxxxx:task/fargate-cluster/d7f4c21df95a4d6b8c04e29119d87e6c --container  fargate-app --interactive --command "ls"
$ aws ecs delete-service --cluster fargate-cluster --service fargate-service --force
```


To test:
```bash
$	curl  <publicIp>:5001/persone
$	curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST <publicIp>:5001/persone
$	curl  <publicIp>:5001/persone
```





# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

