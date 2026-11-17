"""Risorsa protetta: risponde solo se il Lambda authorizer ha accettato il token."""

import json


def handler(event, context):
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"messaggio": "Accesso autorizzato alla risorsa protetta!",
                            "utente": authorizer.get("user")}),
    }
