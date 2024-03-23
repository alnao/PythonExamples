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

# commands to create and run a image in local machine:
#    $ docker build . -t api-persone-nodb
#    $ docker run -it --rm -d -p 5001:5001 api-persone-nodb
#    $ docker ps --latest
#       nota: bash into docker
#           $ docker exec -t -i $(docker ps -q) /bin/bash
#    $ docker stop $(docker ps -q)
#    $ docker rm $(docker ps -a -q)

# TO TEST in localhost
# curl  localhost:5001/persone
# curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST localhost:5001/persone

# command to AWS-ECR repository (see https://medium.com/codex/run-a-python-code-on-aws-batch-part-2-uploading-data-to-ecr-and-creation-of-computing-c5dab12cd3eb)
#    aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin xxxxx.dkr.ecr.eu-west-1.amazonaws.com
#    docker build -t xxxxx-ecs-repo-uno .
#    docker tag xxxxx-ecs-repo-uno:latest xxxxx.dkr.ecr.eu-west-1.amazonaws.com/xxxxx-ecs-repo-uno:latest
#    docker push xxxxx.dkr.ecr.eu-west-1.amazonaws.com/xxxxx-ecs-repo-uno:latest

# RUN on ECS
#	$ aws ecs register-task-definition --cli-input-json file://taskECS.json
#		"taskDefinition": {
#        "taskDefinitionArn": "arn:aws:ecs:eu-west-1:xxxxxx:task-definition/api-persone-nodb:1",
#        "containerDefinitions": [
#            {
#                "name": "api-persone-nodb",
#                "image": "xxxxxx.dkr.ecr.eu-west-1.amazonaws.com/formazione-ecs-repo-uno:latest",
#	$ aws ecs run-task --cluster docker-cluster --task-definition api-persone-nodb:2 --count 1
#	$ aws ecs list-tasks --cluster docker-cluster 
# to test
#   $ curl  3.253.67.174:5001/persone
#   $ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST 3.253.67.174:5001/persone
#	$ aws ecs stop-task --cluster docker-cluster --task xxxx

# RUN on ECS multiple tasks with different ports (bridge system)
#       see bridge network in https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#network_mode
#   mettendo "hostPort": 0, 
#	$ aws ecs register-task-definition --cli-input-json file://taskECSbridge.json
#	$ aws ecs run-task --cluster docker-cluster --task-definition api-persone-nodb:3 --count 1
#	$ aws ecs list-tasks --cluster docker-cluster 
#   $ curl  3.253.67.174:32770/persone
#   $ curl  3.253.67.174:32769/persone
#   $ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST 3.253.67.174:32770/persone
#   $ curl  3.253.67.174:32770/persone
#   $ curl  3.253.67.174:32769/persone
#	$ aws ecs stop-task --cluster docker-cluster --task 52020c440cf64088b946c2f80ff26514
#	$ aws ecs stop-task --cluster docker-cluster --task 6f4d3e6ff1d743b7b4c814fc68e2c411
#	$ aws ecs stop-task --cluster docker-cluster --task 8493986540274fb7a803a30482b7a9c9

# RUN on AWS with Fargate
#	aws ecs create-cluster --cluster-name fargate-cluster
#   che IAM RULE with AmazonEC2ContainerRegistryFullAccess, AmazonECS_FullAccess, AmazonSSMManagedInstanceCore	
#       trust with {"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"},"Action": "sts:AssumeRole"}
#       see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/example_task_definitions.html
#	aws ecs register-task-definition --cli-input-json file://taskECSwithFargate.json
#		"taskDefinitionArn": "arn:aws:ecs:eu-west-1:xxxxxx:task-definition/api-persone-nodb-farg:1",
#	aws ecs list-task-definitions
# run in public subnet
# 	aws ecs create-service --cluster fargate-cluster --service-name fargate-service --task-definition api-persone-nodb-farg:1 --desired-count 1 --launch-type "FARGATE" --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}" --enable-execute-command
#	    in private: aws ecs create-service --cluster fargate-cluster --service-name fargate-service --task-definition sample-fargate:1 --desired-count 1 --launch-type "FARGATE" --network-configuration "awsvpcConfiguration={subnets=[subnet-abcd1234],securityGroups=[sg-abcd1234]}" --enable-execute-command
# 	aws ecs list-services --cluster fargate-cluster
#	aws ecs describe-services --cluster fargate-cluster --services fargate-service
#	aws ecs list-tasks --cluster fargate-cluster --service fargate-service
#	aws ecs describe-tasks --cluster fargate-cluster --tasks arn:aws:ecs:eu-west-1:xxxxxx:task/fargate-cluster/d7f4c21df95a4d6b8c04e29119d87e6c
#	aws ec2 describe-network-interfaces --network-interface-id eni-029e3d81b30cd9da2
# check ip in console 
#	$ curl  <publicIp>:5001/persone
#	$ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST <publicIp>:5001/persone
#	$ curl  <publicIp>:5001/persone
#       see tool https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-windows.html
#	$ aws ecs execute-command --cluster fargate-cluster  --task arn:aws:ecs:eu-west-1:xxxxxx:task/fargate-cluster/d7f4c21df95a4d6b8c04e29119d87e6c --container  fargate-app --interactive --command "ls"
# 	$ aws ecs delete-service --cluster fargate-cluster --service fargate-service --force

# To test
#   $ curl  ip:5001/persone
#   $ curl -d '{"nome":"Andrea", "cognome":"Nao"}' -H "Content-Type: application/json" -X POST ip:5001/persone
