"""
Servizi della sezione Manager: le classi di AWS/SDK riscritte per ricevere una sessione
boto3 gia' legata a profilo e region (vedi common.aws_session), invece di cambiare la
sessione di default di boto3 a ogni chiamata.
"""


def paginate(client, operation, key, limit=None, **kwargs):
    """Tutti gli elementi di un'operazione paginata (al massimo limit, se indicato)."""
    items = []
    for page in client.get_paginator(operation).paginate(**kwargs):
        items.extend(page.get(key, []))
        if limit and len(items) >= limit:
            return items[:limit]
    return items


def name_tag(tags):
    """Valore del tag Name in una lista [{'Key', 'Value'}] di AWS."""
    return next((t['Value'] for t in tags or [] if t.get('Key') == 'Name'), '')
