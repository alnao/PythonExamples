"""
CloudFormation - risorse gestite da CloudFormation nella region scelta o in tutte.

La pagina non legge nulla all'apertura: si sceglie la region (o Tutte) e si preme
"Carica". Stack e risorse si leggono con describe_stacks e list_stack_resources, i tag
delle risorse dalla Tagging API con la cache del Tag Manager (vedi
aws/cloudformation_resources.py). Tutte letture gratuite.

Permessi IAM: cloudformation:DescribeStacks, cloudformation:ListStackResources,
tag:GetResources.
"""

import time

from flask import Blueprint, jsonify, render_template, request

from aws.cloudformation_resources import collect
from common import api_errors, current_profile, current_region, load_config, region_list
from sections.tagmanager import region_resources

bp = Blueprint('cloudformation', __name__)


@bp.route('/cloudformation')
def index():
    config = load_config()
    return render_template('cloudformation.html',
                           suggested_tags=config['suggested_tags'],
                           required_tags=config['tag_manager']['required_tags'],
                           prefix_match_keys=config['tag_manager']['prefix_match_keys'])


@bp.route('/api/cloudformation/resources')
@api_errors
def resources():
    """
    Stack e risorse.

    Query params:
        region: una region o '__all__' (tutte quelle della lista)
        refresh: 1 = rilegge i tag da AWS invece della cache del Tag Manager
    """
    profile = current_profile()
    region = current_region()
    refresh = request.args.get('refresh') == '1'
    started = time.time()
    data = collect(profile, region_list(region),
                   lambda r: region_resources(profile, r, 'tagging', refresh)[0]['resources'])
    return jsonify({'region': region, **data, 'elapsed': round(time.time() - started, 1)})
