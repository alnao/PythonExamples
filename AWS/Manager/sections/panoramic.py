"""
Panoramic - panoramica delle risorse dell'account (ex AWS/Managers/PanoramicResources).

La pagina non legge nulla all'apertura: i pulsanti "Servizi principali" (elenco in
config.json, panoramic.main_services) e "Tutti i servizi" leggono le risorse della
region scelta, o di tutte le region della lista.
"""

from flask import Blueprint, jsonify, render_template, request

from aws.panoramic import SERVICES, collect
from common import ALL, api_errors, current_profile, current_region, load_config, region_list
from sections.tagmanager import TagLookup

bp = Blueprint('panoramic', __name__)


@bp.route('/panoramic')
def index():
    config = load_config()
    return render_template('panoramic.html',
                           services=[{'key': s[0], 'title': s[1], 'global': s[2]} for s in SERVICES],
                           main_services=config['panoramic']['main_services'],
                           suggested_tags=config['suggested_tags'],
                           prefix_match_keys=config['tag_manager']['prefix_match_keys'])


@bp.route('/api/panoramic/resources')
@api_errors
def resources():
    """
    Risorse per servizio.

    Query params:
        scope: main (servizi principali, default) | all (tutti i servizi)
        region: una region o '__all__' (tutte quelle della lista)
    """
    scope = request.args.get('scope', 'main')
    region = current_region()
    keys = [s[0] for s in SERVICES] if scope == 'all' else load_config()['panoramic']['main_services']
    profile = current_profile()
    data = collect(profile, region_list(region), keys, multi_region=region == ALL)
    # tag di ogni riga per le icone: dalla lettura stessa o dalla Tagging API per ARN; ogni
    # lettura del Panoramic e' esplicita, quindi rilegge anche la cache dei tag (refresh)
    rows, entries = [], []
    for section in data['sections']:
        for row in section['rows']:
            entry = ('inline', row.pop('_tags')) if '_tags' in row else \
                ('arn', row.pop('_arn')) if '_arn' in row else None
            if entry:
                rows.append(row)
                entries.append((entry, ''))
    try:
        tags = TagLookup(profile, refresh=True).resolve_all(entries)
    except Exception:
        tags = [None] * len(rows)
    for row, row_tags in zip(rows, tags):
        row['_tags'] = row_tags
    return jsonify({'scope': scope, 'region': region, **data})
