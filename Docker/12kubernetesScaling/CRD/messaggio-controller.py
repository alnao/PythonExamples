import kopf
import logging

@kopf.on.create('example.alnao.it', 'v1', 'messaggi')
def create_fn(spec, name, namespace, logger, **kwargs):
    message = spec.get('message', 'Nessun messaggio specificato')
    logger.info(f"[CREATE] Alnao '{name}' creato nel namespace '{namespace}' con messaggio: {message}")

@kopf.on.update('example.alnao.it', 'v1', 'messaggi')
def update_fn(spec, name, namespace, logger, **kwargs):
    message = spec.get('message', 'Nessun messaggio aggiornato')
    logger.info(f"[UPDATE] Alnao '{name}' aggiornato nel namespace '{namespace}' con messaggio: {message}")

@kopf.on.delete('example.alnao.it', 'v1', 'messaggi')
def delete_fn(name, namespace, logger, **kwargs):
    logger.info(f"[DELETE] Alnao '{name}' eliminato dal namespace '{namespace}'")
