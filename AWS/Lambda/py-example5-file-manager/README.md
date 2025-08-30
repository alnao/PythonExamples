# AwsLambdaExamples

## py-example5-image-manager

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
$ sls create --template aws-python3 --path py-example5-image-manager
```

Check `yml` file to bucket roles , destination is created inside yml, it doen't work if bucket is create manually!

To deploy

```
$ sls deploy -v
```

To run copy a txt file inside the S3 source bucket & check in S3 destination is there is a new file!

To destroy ALL components (with entpy S3 bucket)

```
$ sls remove
```
