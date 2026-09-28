"""
CloudWatch - allarmi e log (ex AWS/Managers/ManagerFlaskCloudWatch).

Funzionalita':
    - allarmi: elenco (anche di tutte le region), filtro per stato, storico, stato forzato,
      attivazione e disattivazione delle azioni, cancellazione, nuovo allarme sulla CPU di un ASG
    - log: log group (filtro per prefisso), stream, ultimi eventi, ricerca con un filter
      pattern, creazione e cancellazione di gruppi e stream, scrittura di un evento

Le API ricevono nomi di gruppi e stream come parametri (non nel percorso), cosi' i
nomi con la barra (/aws/lambda/...) non danno problemi.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request

from aws.cloudwatch_manager import CloudWatchAlarmManager, CloudWatchLogsManager
from common import (api_errors, aws_session, current_profile, current_region, load_config,
                    region_list, run_parallel)

bp = Blueprint('cloudwatch', __name__)


def alarms(region=None):
    return CloudWatchAlarmManager(aws_session(current_profile(), region or current_region(False)))


def logs(region=None):
    return CloudWatchLogsManager(aws_session(current_profile(), region or current_region(False)))


def body():
    return request.get_json(silent=True) or {}


def required(data, *names):
    """Valori obbligatori del corpo della richiesta."""
    missing = [n for n in names if data.get(n) in (None, '')]
    if missing:
        raise ValueError(f"Parametri obbligatori mancanti: {', '.join(missing)}")
    return [data[n] for n in names]


def in_regions(fn):
    """fn(region) su una o tutte le region: (elementi con _region, warnings)."""
    items, warnings = [], []
    for r, res, err in run_parallel(region_list(current_region()), fn):
        if err:
            warnings.append(f"{r}: {err}")
            continue
        for item in res:
            item['_region'] = r
            items.append(item)
    return items, warnings


@bp.route('/cloudwatch')
def index():
    return render_template('cloudwatch.html')


# ----------------------------------------------------------------------
# Allarmi
# ----------------------------------------------------------------------

@bp.route('/api/cloudwatch/alarms')
@api_errors
def list_alarms():
    """Allarmi della region (o di tutte); state = OK | ALARM | INSUFFICIENT_DATA."""
    state = request.args.get('state') or None
    profile = current_profile()
    items, warnings = in_regions(
        lambda r: CloudWatchAlarmManager(aws_session(profile, r)).list_alarms(state_value=state))
    return jsonify({'alarms': items, 'warnings': warnings})


@bp.route('/api/cloudwatch/alarms/history')
@api_errors
def alarm_history():
    name = request.args.get('name', '')
    return jsonify({'history': alarms().get_alarm_history(name)})


@bp.route('/api/cloudwatch/alarms/state', methods=['POST'])
@api_errors
def set_alarm_state():
    data = body()
    name, state, reason = required(data, 'name', 'state', 'reason')
    if state not in ('OK', 'ALARM', 'INSUFFICIENT_DATA'):
        raise ValueError(f"Stato non valido: {state}")
    alarms().set_alarm_state(name, state, reason)
    return jsonify({'message': f"Allarme {name} portato in stato {state}"})


@bp.route('/api/cloudwatch/alarms/actions', methods=['POST'])
@api_errors
def alarm_actions():
    data = body()
    name, = required(data, 'name')
    manager = alarms()
    if data.get('enabled'):
        manager.enable_alarm_actions([name])
        return jsonify({'message': f"Azioni dell'allarme {name} attivate"})
    manager.disable_alarm_actions([name])
    return jsonify({'message': f"Azioni dell'allarme {name} disattivate"})


@bp.route('/api/cloudwatch/alarms/delete', methods=['POST'])
@api_errors
def delete_alarm():
    name, = required(body(), 'name')
    alarms().delete_alarms([name])
    return jsonify({'message': f"Allarme {name} cancellato"})


@bp.route('/api/cloudwatch/alarms/create', methods=['POST'])
@api_errors
def create_alarm():
    """Nuovo allarme sulla CPU media di un Auto Scaling Group."""
    data = body()
    name, asg = required(data, 'alarm_name', 'asg_name')
    alarms().create_cpu_alarm(alarm_name=name, asg_name=asg,
                              threshold=float(data.get('threshold', 80)),
                              evaluation_periods=int(data.get('evaluation_periods', 2)),
                              period=int(data.get('period', 300)))
    return jsonify({'message': f"Allarme {name} creato"})


# ----------------------------------------------------------------------
# Log
# ----------------------------------------------------------------------

@bp.route('/api/cloudwatch/logs/groups')
@api_errors
def list_log_groups():
    prefix = request.args.get('prefix') or None
    profile = current_profile()
    items, warnings = in_regions(
        lambda r: CloudWatchLogsManager(aws_session(profile, r)).list_log_groups(prefix=prefix))
    return jsonify({'groups': items, 'warnings': warnings})


@bp.route('/api/cloudwatch/logs/groups/create', methods=['POST'])
@api_errors
def create_log_group():
    data = body()
    name, = required(data, 'name')
    logs().create_log_group(name, retention_days=int(data.get('retention_days') or 0))
    return jsonify({'message': f"Log group {name} creato"})


@bp.route('/api/cloudwatch/logs/groups/delete', methods=['POST'])
@api_errors
def delete_log_group():
    name, = required(body(), 'name')
    logs().delete_log_group(name)
    return jsonify({'message': f"Log group {name} cancellato"})


@bp.route('/api/cloudwatch/logs/streams')
@api_errors
def list_log_streams():
    group = request.args.get('group', '')
    return jsonify({'streams': logs().list_log_streams(group, limit=int(load_config()['manager']['logs_limit']))})


@bp.route('/api/cloudwatch/logs/streams/create', methods=['POST'])
@api_errors
def create_log_stream():
    group, stream = required(body(), 'group', 'stream')
    logs().create_log_stream(group, stream)
    return jsonify({'message': f"Stream {stream} creato"})


@bp.route('/api/cloudwatch/logs/streams/delete', methods=['POST'])
@api_errors
def delete_log_stream():
    group, stream = required(body(), 'group', 'stream')
    logs().delete_log_stream(group, stream)
    return jsonify({'message': f"Stream {stream} cancellato"})


@bp.route('/api/cloudwatch/logs/events')
@api_errors
def get_log_events():
    """Ultimi eventi di uno stream."""
    limit = int(request.args.get('limit') or load_config()['manager']['logs_limit'])
    events = logs().get_log_events(request.args.get('group', ''), request.args.get('stream', ''), limit=limit)
    return jsonify({'events': events})


@bp.route('/api/cloudwatch/logs/events/put', methods=['POST'])
@api_errors
def put_log_event():
    group, stream, message = required(body(), 'group', 'stream', 'message')
    logs().put_log_events(group, stream, [message])
    return jsonify({'message': 'Evento scritto'})


@bp.route('/api/cloudwatch/logs/filter')
@api_errors
def filter_log_events():
    """Eventi del gruppo che corrispondono al filter pattern nelle ultime N ore (default 24)."""
    hours = int(request.args.get('hours') or 24)
    events = logs().filter_log_events(request.args.get('group', ''), request.args.get('pattern', ''),
                                      start_time=datetime.now() - timedelta(hours=hours),
                                      limit=int(load_config()['manager']['logs_limit']))
    return jsonify({'events': events})
