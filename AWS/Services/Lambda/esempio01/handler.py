import json
import os

def hello(event, context):
    print("esempio01", event)
    body = {
        "message": "Go Serverless v4.0! Your function executed successfully!"
    }

    if 'PARAM' in os.environ:
        param=os.environ['PARAM']
        body = {
            "message": f"Go Serverless v4.0! Your function executed successfully with param {param}!"
        }

    return {"statusCode": 200, "body": json.dumps(body)}
