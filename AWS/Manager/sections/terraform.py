"""
Terraform - risorse gestite da Terraform, lette dagli state sui bucket S3 configurati
(config.json, terraform.buckets).

La pagina non legge nulla all'apertura: si sceglie un bucket (o tutti) e si preme
"Carica". Le letture (ListObjectsV2 e GetObject sugli state) sono letture S3 normali.
Al browser arrivano solo indirizzo, tipo, nome, id, ARN, region e tag di ogni risorsa,
mai gli altri attributi degli state (vedi aws/terraform_states.py).

Permessi IAM necessari: s3:ListBucket e s3:GetObject sui bucket degli state.
"""

import time

from flask import Blueprint, jsonify, render_template, request

from aws.terraform_states import collect
from common import api_errors, current_profile, load_config

bp = Blueprint('terraform', __name__)


@bp.route('/terraform')
def index():
    config = load_config()
    return render_template('terraform.html', buckets=config['terraform']['buckets'],
                           suggested_tags=config['suggested_tags'],
                           required_tags=config['tag_manager']['required_tags'],
                           prefix_match_keys=config['tag_manager']['prefix_match_keys'])


@bp.route('/api/terraform/resources')
@api_errors
def resources():
    """
    Risorse degli state.

    Query params:
        bucket: uno dei bucket di terraform.buckets, oppure vuoto per tutti
    """
    tf = load_config()['terraform']
    bucket = request.args.get('bucket', '')
    if bucket and bucket not in tf['buckets']:
        raise ValueError(f"Bucket non in configurazione: {bucket}")
    started = time.time()
    data = collect(current_profile(), [bucket] if bucket else list(tf['buckets']),
                   tuple(tf['state_suffixes']), int(tf['max_states']))
    return jsonify({**data, 'elapsed': round(time.time() - started, 1)})
