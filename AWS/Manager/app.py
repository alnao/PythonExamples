"""
AlNao AWS Manager - un'unica applicazione Flask e Bootstrap che riunisce i tool di AWS/Managers.

Sezioni (una voce della navbar ciascuna, un blueprint in sections/):
    - Home           riepilogo dei costi (solo cache, gratis) e delle risorse attive
    - Cost Explorer  costi per servizio e per tag, cache per mese e Data Export (ex CostExplorer)
    - Panoramic      panoramica delle risorse dell'account (ex PanoramicResources)
    - Tag Manager    elenco e modifica dei tag delle risorse, report multi-region (ex TagManager)
    - Manager        gestione dei singoli servizi: S3, EC2, Lambda, SQS... (ex ManagerFlask)
    - CloudWatch     allarmi e log (ex ManagerFlaskCloudWatch)
    - Terraform      risorse gestite da Terraform, dagli state sui bucket S3 configurati
    - CloudFormation risorse gestite da CloudFormation, stack per stack, con i tag

Il profilo AWS si sceglie nella navbar, la region dentro le sezioni che la usano
(con l'opzione "Tutte" dove possibile). Ogni operazione che modifica risorse AWS chiede
conferma nella pagina.

Per eseguirlo:
    - installare le librerie con il requirements.txt
        pip3 install -r requirements.txt
    - configurare le credenziali AWS (~/.aws/credentials o variabili d'ambiente)
    - lanciare lo script:
        python3 app.py
    - aprire il browser alla pagina:
        http://localhost:5042
"""

import logging
import os

from flask import Flask, jsonify, render_template, request, session

from common import ALL, JsonProvider, list_profiles, load_config
from sections import cloudformation, cloudwatch, costexplorer, home, manager, panoramic, tagmanager, terraform

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.json = JsonProvider(app)
# La sessione (cookie firmato) contiene solo il profilo e la region scelti
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'alnao-aws-manager-locale')
app.config['MAX_CONTENT_LENGTH'] = int(load_config()['manager']['max_upload_mb']) * 1024 * 1024

for section in (home, costexplorer, panoramic, tagmanager, manager, cloudwatch, terraform, cloudformation):
    app.register_blueprint(section.bp)

# Voci della navbar: (blueprint, endpoint, etichetta, icona)
NAV = [
    ('home', 'home.index', 'Home', 'fa-house'),
    ('costexplorer', 'costexplorer.index', 'Cost Explorer', 'fa-coins'),
    ('panoramic', 'panoramic.index', 'Panoramic', 'fa-binoculars'),
    ('tagmanager', 'tagmanager.index', 'Tag Manager', 'fa-tags'),
    ('manager', 'manager.index', 'Manager', 'fa-screwdriver-wrench'),
    ('cloudwatch', 'cloudwatch.index', 'CloudWatch', 'fa-chart-line'),
    ('terraform', 'terraform.index', 'Terraform', 'fa-cubes-stacked'),
    ('cloudformation', 'cloudformation.index', 'CloudFormation', 'fa-layer-group'),
]


@app.context_processor
def page_context():
    """Dati comuni a tutte le pagine: navbar, profili, region."""
    config = load_config()
    session.setdefault('profile', config['default_profile'])
    session.setdefault('region', config['default_region'])
    return {
        'nav': NAV,
        'profiles': list_profiles(),
        'current_profile': session['profile'],
        'regions': config['regions'],
        'current_region': session['region'],
        'ALL': ALL,
        # regole dei tag per le icone di Manager e Panoramic (tagIcon in common.js)
        'tag_rules': {
            'required': config['tag_manager']['required_tags'],
            'standard': list(config['suggested_tags'].keys()),
            'compliant': config['compliant_tags'].get('sets', []),
            'auto': 'aws_auto',
        },
    }


@app.route('/api/context', methods=['POST'])
def set_context():
    """Salva nella sessione il profilo (navbar) e/o la region (sezioni) scelti."""
    data = request.get_json(silent=True) or {}
    config = load_config()
    profile, region = data.get('profile'), data.get('region')
    if profile:
        if profile not in list_profiles():
            return jsonify({'error': f'Profilo sconosciuto: {profile}'}), 400
        session['profile'] = profile
    if region:
        if region != ALL and region not in config['regions']:
            return jsonify({'error': f'Region non in lista: {region}'}), 400
        session['region'] = region
    return jsonify({'profile': session.get('profile'), 'region': session.get('region')})


@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Risorsa non trovata'}), 404
    return render_template('error.html', message='Pagina non trovata'), 404


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    port = int(os.getenv('PORT', load_config()['port']))
    # solo in locale: l'app puo' modificare risorse AWS (HOST=0.0.0.0 per esporla in rete)
    app.run(host=os.getenv('HOST', '127.0.0.1'), port=port, debug=True)
