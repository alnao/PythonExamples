from flask import Flask, render_template, jsonify
import boto3
from botocore.exceptions import ClientError
import json
from datetime import datetime
import os

app = Flask(__name__)

# Configurazione DynamoDB
DYNAMODB_ENDPOINT = os.getenv('DYNAMODB_ENDPOINT', 'http://dynamodb-local:8000')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'alberto-dy2')
DYNAMODB_REGION = os.getenv('DYNAMODB_REGION', 'us-east-1')

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'alberto-dy2')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'alberto-dy2')

# Setup DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=DYNAMODB_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

table = dynamodb.Table(DYNAMODB_TABLE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/items')
def get_items():
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # Converti timestamp e formatta i dati
        for item in items:
            if 'processed_at' in item:
                try:
                    timestamp = int(item['processed_at'])
                    item['processed_at_formatted'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    item['processed_at_formatted'] = 'N/A'
            
            # Decodifica JSON se necessario
            if 'original_message' in item:
                try:
                    item['original_message_parsed'] = json.loads(item['original_message'])
                except:
                    item['original_message_parsed'] = item['original_message']
            
            if 'api_result' in item:
                try:
                    item['api_result_parsed'] = json.loads(item['api_result'])
                except:
                    item['api_result_parsed'] = item['api_result']
        
        # Ordina per timestamp (più recenti prima)
        items.sort(key=lambda x: x.get('processed_at', 0), reverse=True)
        
        return jsonify({
            'success': True,
            'items': items,
            'count': len(items)
        })
    
    except ClientError as e:
        return jsonify({
            'success': False,
            'error': f'DynamoDB Error: {e.response["Error"]["Message"]}'
        }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500

@app.route('/api/item/<item_id>')
def get_item(item_id):
    try:
        response = table.get_item(Key={'id': item_id})
        item = response.get('Item')
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        return jsonify({
            'success': True,
            'item': item
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        stats = {
            'total_items': len(items),
            'consumers': len(set(item.get('consumer_id', 'unknown') for item in items)),
            'api_success': len([item for item in items if item.get('api_status') == 'processed']),
            'recent_items': len([item for item in items if 
                               int(item.get('processed_at', 0)) > (datetime.now().timestamp() - 3600)])
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)