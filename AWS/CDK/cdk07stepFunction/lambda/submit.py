"""Primo passo della Step Function: "avvia" un job simulato e ne restituisce lo stato iniziale.

Input facoltativo: {"steps": <controlli prima della fine, default 2>, "fail": <true per far fallire il job>}
"""

import uuid


def lambda_handler(event, context):
    event = event or {}
    return {
        "jobId": str(uuid.uuid4()),
        "status": "RUNNING",
        "checks": 0,
        "steps": int(event.get("steps", 2)),
        "fail": bool(event.get("fail", False)),
    }
