from flask import Flask, render_template, jsonify, request
from cloudwatch_manager import CloudWatchAlarmManager,CloudWatchLogsManager
import logging
from typing import Dict, Any
from functools import wraps
from datetime import datetime
from urllib.parse import unquote
import os

"""
Esempio creato con claude
- mi descrivi i princiapali comandi AWS CLI per cloudwatch alarm? esiste un comando per forzare un allarme di un alert?
- adesso mi scrivi una classe python con AWS sdk per gestire le principali funzionalità di cloudwatch alarm ?
- scrivi una pagina html e javascript, usando la libreria grafica bootstrap per chiamare queste funzioni
- ora creami un template flask che usi la classe python
- adesso mi scrivi una classe python con AWS sdk per gestire le principali funzionalità di cloudwatch logs ?
- ora inegra il flask per questi metodi
- modifica il template html, voglio che abbia due tab, il primo per cloudwatch alarms che già abbiamo e il secondo per un secondo tab per la gestione dei log
- ho un errore perchè il nome del log groups contiene il carattere / , correggi
- ho un errore per quei gruppi il cui nome inizia per barra /

to run: 'python app.py'
"""

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize CloudWatch manager
try:
    # You can set these as environment variables
    region = os.getenv('AWS_REGION', 'eu-west-1')
    aws_profile = os.getenv('AWS_PROFILE', None)
    
    cloudwatch = CloudWatchAlarmManager(
        region_name=region,
        aws_profile=aws_profile
    )
    logs_manager = CloudWatchLogsManager(
        region_name=region,
        aws_profile=aws_profile
    )
except Exception as e:
    logger.error(f"Failed to initialize CloudWatch manager: {e}")
    raise

def handle_aws_errors(f):
    """Decorator to handle AWS errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"AWS Error in {f.__name__}: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return decorated_function

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/api/create-alarm', methods=['POST'])
@handle_aws_errors
def create_alarm():
    """Create a new CPU alarm"""
    data = request.json
    
    response = cloudwatch.create_cpu_alarm(
        alarm_name=data['alarm_name'],
        asg_name=data['asg_name'],
        threshold=float(data['threshold']),
        evaluation_periods=int(data['evaluation_periods']),
        period=int(data['period'])
    )
    
    return jsonify({'message': 'Alarm created successfully', 'response': response})

@app.route('/api/list-alarms')
@handle_aws_errors
def list_alarms():
    """List all CloudWatch alarms"""
    state = request.args.get('state', None)
    alarms = cloudwatch.list_alarms(state_value=state)
    return jsonify(alarms)

@app.route('/api/alarm-history/<alarm_name>')
@handle_aws_errors
def get_alarm_history(alarm_name: str):
    """Get history for a specific alarm"""
    history = cloudwatch.get_alarm_history(alarm_name)
    return jsonify(history)

@app.route('/api/set-alarm-state', methods=['POST'])
@handle_aws_errors
def set_alarm_state():
    """Manually set an alarm's state"""
    data = request.json
    response = cloudwatch.set_alarm_state(
        alarm_name=data['alarm_name'],
        state_value=data['state_value'],
        reason=data['reason']
    )
    return jsonify({'message': 'Alarm state updated successfully', 'response': response})

@app.route('/api/delete-alarm/<alarm_name>', methods=['DELETE'])
@handle_aws_errors
def delete_alarm(alarm_name: str):
    """Delete a specific alarm"""
    response = cloudwatch.delete_alarms([alarm_name])
    return jsonify({'message': 'Alarm deleted successfully', 'response': response})

@app.route('/api/enable-alarm/<alarm_name>', methods=['POST'])
@handle_aws_errors
def enable_alarm(alarm_name: str):
    """Enable actions for an alarm"""
    response = cloudwatch.enable_alarm_actions([alarm_name])
    return jsonify({'message': 'Alarm actions enabled', 'response': response})

@app.route('/api/disable-alarm/<alarm_name>', methods=['POST'])
@handle_aws_errors
def disable_alarm(alarm_name: str):
    """Disable actions for an alarm"""
    response = cloudwatch.disable_alarm_actions([alarm_name])
    return jsonify({'message': 'Alarm actions disabled', 'response': response})


# Log Groups Management
@app.route('/api/log-groups', methods=['GET'])
@handle_aws_errors
def list_log_groups():
    """List all log groups"""
    prefix = request.args.get('prefix', None)
    groups = list(logs_manager.list_log_groups(prefix=prefix))
    return jsonify(groups)

@app.route('/api/log-groups', methods=['POST'])
@handle_aws_errors
def create_log_group():
    """Create a new log group"""
    data = request.json
    response = logs_manager.create_log_group(
        log_group_name=data['log_group_name'],
        retention_days=data.get('retention_days', 30),
        tags=data.get('tags', None)
    )
    return jsonify({'message': 'Log group created successfully', 'response': response})

# Log Streams Management
@app.route('/api/log-groups/<path:log_group_name>/streams')
@handle_aws_errors
def list_log_streams(log_group_name: str):
    """List all log streams in a log group"""
    # Decodifica il path e gestisci la barra iniziale
    log_group_name = unquote(log_group_name)
    if not log_group_name.startswith('/'):
        log_group_name = '/' + log_group_name
        
    prefix = request.args.get('prefix', None)
    order_by = request.args.get('orderBy', 'LogStreamName')
    descending = request.args.get('descending', 'false').lower() == 'true'
    
    streams = list(logs_manager.list_log_streams(
        log_group_name=log_group_name,
        prefix=prefix,
        orderBy=order_by,
        descending=descending
    ))
    return jsonify(streams)

@app.route('/api/log-groups/<path:log_group_name>/streams', methods=['POST'])
@handle_aws_errors
def create_log_stream(log_group_name: str):
    """Create a new log stream"""
    data = request.json
    response = logs_manager.create_log_stream(
        log_group_name=log_group_name,
        log_stream_name=data['log_stream_name']
    )
    return jsonify({'message': 'Log stream created successfully', 'response': response})

@app.route('/api/log-groups/<path:log_group_name>', methods=['DELETE'])
@handle_aws_errors
def delete_log_group(log_group_name: str):
    """Delete a log group"""
    # Decodifica il path e gestisci la barra iniziale
    log_group_name = unquote(log_group_name)
    if not log_group_name.startswith('/'):
        log_group_name = '/' + log_group_name
        
    response = logs_manager.delete_log_group(log_group_name)
    return jsonify({'message': 'Log group deleted successfully', 'response': response})

# Log Events Management

@app.route('/api/log-groups/<path:log_group_name>/streams/<path:log_stream_name>/events')
@handle_aws_errors
def get_log_events(log_group_name: str, log_stream_name: str):
    """Get log events from a stream"""
    # Decodifica entrambi i path
    log_group_name = unquote(log_group_name)
    log_stream_name = unquote(log_stream_name)
    
    # Gestisci la barra iniziale per il log group
    if not log_group_name.startswith('/'):
        log_group_name = '/' + log_group_name

    """Get log events from a stream"""
    start_time = request.args.get('start_time', None)
    end_time = request.args.get('end_time', None)
    limit = request.args.get('limit', None)
    next_token = request.args.get('next_token', None)
    
    kwargs = {
        'log_group_name': log_group_name,
        'log_stream_name': log_stream_name
    }
    
    if start_time:
        kwargs['start_time'] = datetime.fromtimestamp(int(start_time))
    if end_time:
        kwargs['end_time'] = datetime.fromtimestamp(int(end_time))
    if limit:
        kwargs['limit'] = int(limit)
    if next_token:
        kwargs['next_token'] = next_token
        
    events = logs_manager.get_log_events(**kwargs)
    return jsonify(events)

@app.route('/api/log-groups/<path:log_group_name>/streams/<path:log_stream_name>/events', methods=['POST'])
@handle_aws_errors
def put_log_events(log_group_name: str, log_stream_name: str):
    """Put log events into a stream"""
    data = request.json
    response = logs_manager.put_log_events(
        log_group_name=log_group_name,
        log_stream_name=log_stream_name,
        events=data['events'],
        sequence_token=data.get('sequence_token', None)
    )
    return jsonify({'message': 'Log events added successfully', 'response': response})

@app.route('/api/log-groups/<path:log_group_name>/filter', methods=['GET'])
@handle_aws_errors
def filter_log_events(log_group_name: str):
    """Filter log events across all streams"""
    filter_pattern = request.args.get('filter_pattern', '')
    start_time = request.args.get('start_time', None)
    end_time = request.args.get('end_time', None)
    limit = request.args.get('limit', None)
    
    kwargs = {
        'log_group_name': log_group_name,
        'filter_pattern': filter_pattern
    }
    
    if start_time:
        kwargs['start_time'] = datetime.fromtimestamp(int(start_time))
    if end_time:
        kwargs['end_time'] = datetime.fromtimestamp(int(end_time))
    if limit:
        kwargs['limit'] = int(limit)
        
    events = list(logs_manager.filter_log_events(**kwargs))
    return jsonify(events)


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Configuration for development
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Run the application
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
