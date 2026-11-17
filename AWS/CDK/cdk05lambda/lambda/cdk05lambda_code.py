"""Lambda di esempio: scrive l'evento nel log e risponde con un saluto.

L'evento puo' contenere il campo "nome"; se manca si usa la variabile d'ambiente DEFAULT_NAME.
"""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("evento ricevuto: %s", json.dumps(event))
    nome = (event or {}).get("nome") or os.environ.get("DEFAULT_NAME", "mondo")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "messaggio": f"Ciao {nome}!",
            "requestId": getattr(context, "aws_request_id", None),
        }),
    }
