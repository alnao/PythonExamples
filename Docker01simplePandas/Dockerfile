#see https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

FROM python:3.8
ADD d.py .
RUN pip install pandas
CMD ["python","./d.py"]

# command to create and run a image in local machine:
    # docker builds -t sample-aws-code .
    # docker run sample-aws-code
    # docker ps --latest

# command to AWS-ECR repository (see https://medium.com/codex/run-a-python-code-on-aws-batch-part-2-uploading-data-to-ecr-and-creation-of-computing-c5dab12cd3eb)
#    aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com
#    docker build -t nome-ecs-repo-uno .
#    docker tag nome-ecs-repo-uno:latest xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
#    docker push xxxxxxx.dkr.ecr.eu-west-1.amazonaws.com/nome-ecs-repo-uno:latest
