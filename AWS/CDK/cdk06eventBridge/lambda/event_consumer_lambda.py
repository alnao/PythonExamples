import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#see https://github.com/aws-samples/aws-cdk-examples/blob/main/python/api-eventbridge-lambda/lambda/event_consumer_lambda.py
def lambda_handler(event, context):
    logger.info(event)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "result": "testing..."
        }),
    }