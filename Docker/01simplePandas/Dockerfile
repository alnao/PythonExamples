#see https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

FROM python:3.8
ADD d.py .
RUN pip install pandas
CMD ["python","./d.py"]
