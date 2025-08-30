# AwsLambdaExamples

## py-example6-sqs-get

Note: in python code there are comments about Image library to create a thumbnail

To use serverless-python-requirement (like npm install)

```
$ serverless plugin install -n serverless-python-requirements
```

For vesion2 of serverless must use a version2 of pacakge
```
npm install -g serverless@2.72.3
```


To create 

```
$ sls create --template aws-python3 --path py-example6-sqs-get
```

Check `yml` file to bucket roles , destination is created inside yml, it doen't work if bucket is create manually!

To deploy

```
$ sls deploy -v
```


To invoke
```
$ sls invoke -f sqsget
```


To destroy ALL components (with entpy S3 bucket)

```
$ sls remove
```
