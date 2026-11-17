"""Lambda iscritta al topic SNS: scrive nel log ogni messaggio ricevuto (con oggetto e attributi)."""

import json


def handler(event, context):
    messages = []
    for record in event.get("Records", []):
        sns = record["Sns"]
        messages.append({"messageId": sns.get("MessageId"), "subject": sns.get("Subject"), "message": sns["Message"]})
        print(f"messaggio ricevuto: {json.dumps(messages[-1])}")
    return {"ricevuti": len(messages), "messaggi": messages}
