#import json

def hello(event, context):
    print("Ciao");
    return "Ciao example1 py";
"""
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
"""