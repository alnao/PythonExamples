"""
Home - riepilogo dei costi e delle risorse attive.

I costi vengono solo dalla cache del Cost Explorer e dal Data Export (gratis): la Home
non fa mai richieste a Cost Explorer, per i mesi mancanti rimanda alla sua pagina.
Le risorse si contano con letture gratuite (describe/list) nella region scelta o in tutte.
"""

from flask import Blueprint, jsonify, render_template

from aws.summary import resource_counts
from common import api_errors, current_profile, current_region, load_config, region_list
from sections.costexplorer import cached_summary

bp = Blueprint('home', __name__)


@bp.route('/')
def index():
    return render_template('home.html',
                           service_aliases=load_config()['cost_explorer']['service_aliases'])


@bp.route('/api/home/costs')
@api_errors
def costs():
    return jsonify(cached_summary(current_profile()))


@bp.route('/api/home/resources')
@api_errors
def resources():
    region = current_region()
    return jsonify({'region': region, **resource_counts(current_profile(), region_list(region))})
