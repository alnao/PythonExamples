"""
Home - riepilogo dei costi e delle risorse attive.

I costi vengono solo dalla cache del Cost Explorer e dal Data Export (gratis): la Home
non fa mai richieste a Cost Explorer, per i mesi mancanti rimanda alla sua pagina.
Le risorse si contano con letture gratuite (describe/list) in tutte le region della lista.
"""

from flask import Blueprint, jsonify, render_template, request

from aws.summary import resource_counts
from common import ALL, api_errors, current_profile, load_config, region_list
from sections.costexplorer import cached_breakdown, cached_summary

bp = Blueprint('home', __name__)

# Tag proposti per primi nella tendina "Raggruppa per" dei costi
FIRST_TAGS = ('Project', 'CostCenter')


def group_tags():
    """Chiavi di suggested_tags per la tendina dei costi: prima Project e CostCenter."""
    keys = list(load_config()['suggested_tags'].keys())
    return [k for k in FIRST_TAGS if k in keys] + [k for k in keys if k not in FIRST_TAGS]


@bp.route('/')
def index():
    return render_template('home.html',
                           service_aliases=load_config()['cost_explorer']['service_aliases'],
                           group_tags=group_tags())


@bp.route('/api/home/costs')
@api_errors
def costs():
    return jsonify(cached_summary(current_profile()))


@bp.route('/api/home/costs/group')
@api_errors
def costs_by_group():
    """Costi per valore di un tag (group=TAG:Project), solo da cache e Data Export."""
    group = request.args.get('group', '')
    if not group.startswith('TAG:'):
        raise ValueError(f"Raggruppamento non valido: {group}")
    return jsonify(cached_breakdown(current_profile(), group))


@bp.route('/api/home/resources')
@api_errors
def resources():
    return jsonify(resource_counts(current_profile(), region_list(ALL)))
