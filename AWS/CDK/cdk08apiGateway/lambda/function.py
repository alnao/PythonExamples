"""Lambda dietro API Gateway: risponde con lo stage dell'API e l'alias della funzione che e' stato invocato.

Dall'esempio aws-samples api-stages-lambda:
https://github.com/aws-samples/aws-cdk-examples/blob/main/python/api-stages-lambda/lambda/lambda-handler.py
"""

import json


def handler(event, context):
    # ARN qualificato: arn:aws:lambda:<region>:<account>:function:<nome>:<alias>
    func_alias = context.invoked_function_arn.rsplit(":", 1)[-1]

    try:
        api_stage = event["stageVariables"]["lambdaAlias"]
    except (KeyError, TypeError):
        return {"statusCode": 404, "body": json.dumps({"msg": "Invalid API path."})}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "msg": f"Congrats! You've successfully hit the {api_stage} API Stage and the {func_alias} Lambda Alias.",
            "apiStage": api_stage,
            "lambdaAlias": func_alias,
        }),
    }
