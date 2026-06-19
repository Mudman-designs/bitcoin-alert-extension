import os
import sys
import json
import time
import math
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

# Print debug info
print(f"Python version: {sys.version}")
print("Starting Bitcoin Alert API...")

app = Flask(__name__)
CORS(app)

print("Flask app created successfully!")

# Simple in-memory storage for alerts
alerts = []
ALERTS_FILE = 'alerts.json'

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_alerts(alerts_data):
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts_data, f, indent=2)

# Load existing alerts
alerts = load_alerts()

# Price cache
price_cache = {
    'data': None,
    'timestamp': None,
    'cache_duration': 15
}

def get_cached_price():
    now = datetime.now()
    
    if (price_cache['timestamp'] and 
        (now - price_cache['timestamp']).total_seconds() < price_cache['cache_duration']):
        print("Using cached price data")
        return price_cache['data']
    
    print("Fetching fresh price data...")
    try:
        time.sleep(0.5)
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        price_cache['data'] = data
        price_cache['timestamp'] = now
        return data
    except Exception as e:
        print(f"Error fetching price: {e}")
        if price_cache['data']:
            print("Using cached data")
            return price_cache['data']
        return None

@app.route('/')
def index():
    return jsonify({
        'status': 'running',
        'message': 'Bitcoin Alert Extension API',
        'version': '1.0'
    })

@app.route('/api/price')
def get_price():
    print("Price endpoint called")
    try:
        data = get_cached_price()
        if data and 'bitcoin' in data:
            return jsonify({
                'price': data['bitcoin']['usd'],
                'volume_24h': data['bitcoin'].get('usd_24h_vol', 0)
            })
        return jsonify({'error': 'No price data available'}), 500
    except Exception as e:
        print(f"Error in price endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    print("Alerts endpoint called")
    return jsonify({'alerts': alerts})

@app.route('/api/set_alert', methods=['POST'])
def set_alert():
    print("Set alert endpoint called")
    try:
        data = request.get_json()
        alert_id = max([a['id'] for a in alerts], default=0) + 1
        
        alert = {
            'id': alert_id,
            'type': data.get('type', 'price'),
            'min_price': data.get('min_price'),
            'max_price': data.get('max_price'),
            'volume_threshold': data.get('volume_threshold'),
            'volatility_threshold': data.get('volatility_threshold'),
            'rsi_threshold': data.get('rsi_threshold'),
            'rsi_direction': data.get('rsi_direction', 'above'),
            'triggered': False,
            'created_at': datetime.now().isoformat()
        }
        
        alerts.append(alert)
        save_alerts(alerts)
        return jsonify({'message': 'Alert set successfully', 'alert': alert})
    except Exception as e:
        print(f"Error setting alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_alert/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    print(f"Delete alert endpoint called: {alert_id}")
    try:
        global alerts
        alerts = [a for a in alerts if a['id'] != alert_id]
        save_alerts(alerts)
        return jsonify({'message': 'Alert deleted successfully'})
    except Exception as e:
        print(f"Error deleting alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_alerts')
def check_alerts():
    print("Check alerts endpoint called")
    try:
        price_data = get_cached_price()
        if price_data and 'bitcoin' in price_data:
            current_price = price_data['bitcoin']['usd']
            return jsonify({
                'current_price': current_price,
                'triggered_alerts': []
            })
        return jsonify({'error': 'No price data'}), 500
    except Exception as e:
        print(f"Error checking alerts: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5601))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
