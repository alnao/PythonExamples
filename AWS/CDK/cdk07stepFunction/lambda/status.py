"""Controllo dello stato del job simulato: dopo "steps" controlli il job termina con SUCCEEDED (o FAILED)."""


def lambda_handler(event, context):
    job = dict(event)
    job["checks"] = job.get("checks", 0) + 1
    if job["checks"] < job.get("steps", 2):
        job["status"] = "RUNNING"
    else:
        job["status"] = "FAILED" if job.get("fail") else "SUCCEEDED"
    return job
