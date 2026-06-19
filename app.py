from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import os
import traceback
import math
from datetime import datetime, timedelta
import time

app = Flask(__name__)
CORS(app)

ALERTS_FILE = 'alerts.json'
HISTORICAL_DATA_FILE = 'historical_data.json'

# Cache for price data to avoid hitting rate limits
price_cache = {
    'data': None,
    'timestamp': None,
    'cache_duration': 15  # Cache for 15 seconds
}

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_alerts(alerts):
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)

def load_historical_data():
    if os.path.exists(HISTORICAL_DATA_FILE):
        try:
            with open(HISTORICAL_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'prices': [], 'volumes': [], 'timestamps': []}
    return {'prices': [], 'volumes': [], 'timestamps': []}

def save_historical_data(data):
    with open(HISTORICAL_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

alerts = load_alerts()
historical_data = load_historical_data()

def get_cached_price():
    """Get price from cache or fetch new data with rate limiting"""
    now = datetime.now()
    
    # Check if cache is valid
    if (price_cache['timestamp'] and 
        (now - price_cache['timestamp']).total_seconds() < price_cache['cache_duration']):
        print("Using cached price data")
        return price_cache['data']
    
    print("Fetching fresh price data from CoinGecko...")
    try:
        time.sleep(0.5)  # Small delay to avoid rate limits
        
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        price_cache['data'] = data
        price_cache['timestamp'] = now
        
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limited by CoinGecko. Using cached data if available.")
            if price_cache['data']:
                return price_cache['data']
        raise
    except Exception as e:
        print(f"Error fetching price: {e}")
        if price_cache['data']:
            print("Using stale cache data")
            return price_cache['data']
        raise

def fetch_ohlcv_data():
    """Fetch OHLCV data with caching"""
    try:
        time.sleep(0.5)  # Small delay
        response = requests.get(
            'https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=30',
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching OHLCV data: {e}")
        return None

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

@app.route('/api/price')
def get_price():
    try:
        data = get_cached_price()
        
        if not data or 'bitcoin' not in data:
            return jsonify({'error': 'No price data available'}), 500
            
        price = data['bitcoin']['usd']
        volume_24h = data['bitcoin'].get('usd_24h_vol', 0)
        
        # Store historical data
        if price:
            historical_data['prices'].append(price)
            historical_data['volumes'].append(volume_24h)
            historical_data['timestamps'].append(datetime.now().isoformat())
            
            if len(historical_data['prices']) > 720:
                historical_data['prices'] = historical_data['prices'][-720:]
                historical_data['volumes'] = historical_data['volumes'][-720:]
                historical_data['timestamps'] = historical_data['timestamps'][-720:]
            
            save_historical_data(historical_data)
        
        return jsonify({'price': price, 'volume_24h': volume_24h})
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_alert', methods=['POST'])
def set_alert():
    try:
        data = request.get_json()
        print(f"Setting alert with data: {data}")
        
        alert_type = data.get('type', 'price')
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        
        # Smart alert parameters
        volume_threshold = data.get('volume_threshold')
        volatility_threshold = data.get('volatility_threshold')
        rsi_threshold = data.get('rsi_threshold')
        rsi_direction = data.get('rsi_direction', 'above')
        
        alert_id = max([a['id'] for a in alerts], default=0) + 1
        
        alert = {
            'id': alert_id,
            'type': alert_type,
            'min_price': min_price,
            'max_price': max_price,
            'volume_threshold': volume_threshold,
            'volatility_threshold': volatility_threshold,
            'rsi_threshold': rsi_threshold,
            'rsi_direction': rsi_direction,
            'triggered': False,
            'created_at': datetime.now().isoformat()
        }
        
        alerts.append(alert)
        save_alerts(alerts)
        
        return jsonify({'message': 'Alert set successfully', 'alert': alert, 'alerts': alerts})
    except Exception as e:
        print(f"Error setting alert: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_alert/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    try:
        global alerts
        alerts = [alert for alert in alerts if alert['id'] != alert_id]
        save_alerts(alerts)
        return jsonify({'message': 'Alert deleted successfully', 'alerts': alerts})
    except Exception as e:
        print(f"Error deleting alert: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    try:
        return jsonify({'alerts': alerts})
    except Exception as e:
        print(f"Error getting alerts: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/check_alerts', methods=['GET'])
def check_alerts():
    try:
        print("Checking smart alerts...")
        
        # Get cached price data
        price_data = get_cached_price()
        if not price_data or 'bitcoin' not in price_data:
            return jsonify({'error': 'No price data available'}), 500
            
        current_price = price_data['bitcoin']['usd']
        current_volume = price_data['bitcoin'].get('usd_24h_vol', 0)
        
        # Fetch OHLCV for indicators (with caching)
        ohlcv_data = fetch_ohlcv_data()
        prices = [candle[4] for candle in ohlcv_data] if ohlcv_data else []
        
        # Calculate indicators
        rsi = calculate_rsi(prices, 14) if prices else None
        ema_50 = calculate_ema(prices, 50) if prices else None
        ema_200 = calculate_ema(prices, 200) if prices else None
        
        # Calculate average volume (last 30 days)
        avg_volume = sum(historical_data['volumes'][-30:]) / 30 if len(historical_data['volumes']) >= 30 else current_volume
        
        # Calculate volatility
        price_changes = []
        for i in range(1, len(historical_data['prices'])):
            if historical_data['prices'][i-1] > 0:
                change = (historical_data['prices'][i] - historical_data['prices'][i-1]) / historical_data['prices'][i-1]
                price_changes.append(change)
        
        volatility = 0
        if price_changes:
            mean_change = sum(price_changes) / len(price_changes)
            variance = sum((x - mean_change) ** 2 for x in price_changes) / len(price_changes)
            volatility = math.sqrt(variance)
        
        triggered_alerts = []
        
        for alert in alerts:
            alert_triggered = False
            trigger_reason = None
            trigger_details = {}
            
            # Check based on alert type
            if alert['type'] == 'price':
                if alert['min_price'] is not None and current_price <= alert['min_price']:
                    alert_triggered = True
                    trigger_reason = f'below ${alert["min_price"]:,.0f}'
                elif alert['max_price'] is not None and current_price >= alert['max_price']:
                    alert_triggered = True
                    trigger_reason = f'above ${alert["max_price"]:,.0f}'
                    
            elif alert['type'] == 'volume_spike':
                if avg_volume > 0 and current_volume > avg_volume * alert['volume_threshold']:
                    alert_triggered = True
                    trigger_reason = f'volume spike: {current_volume/avg_volume:.1f}x average'
                    trigger_details['volume_ratio'] = current_volume/avg_volume
                    
            elif alert['type'] == 'volatility_shift':
                if volatility > alert['volatility_threshold']:
                    alert_triggered = True
                    trigger_reason = f'volatility spike: {volatility:.2%}'
                    trigger_details['volatility'] = volatility
                    
            elif alert['type'] == 'rsi':
                if rsi is not None:
                    if alert['rsi_direction'] == 'above' and rsi >= alert['rsi_threshold']:
                        alert_triggered = True
                        trigger_reason = f'RSI above {alert["rsi_threshold"]} (overbought)'
                        trigger_details['rsi'] = rsi
                    elif alert['rsi_direction'] == 'below' and rsi <= alert['rsi_threshold']:
                        alert_triggered = True
                        trigger_reason = f'RSI below {alert["rsi_threshold"]} (oversold)'
                        trigger_details['rsi'] = rsi
                        
            elif alert['type'] == 'golden_cross':
                if ema_50 is not None and ema_200 is not None:
                    if ema_50 > ema_200 and not alert.get('cross_triggered', False):
                        alert_triggered = True
                        trigger_reason = 'Golden Cross! 50-day EMA above 200-day EMA (BULLISH)'
                        trigger_details['ema_50'] = ema_50
                        trigger_details['ema_200'] = ema_200
                        alert['cross_triggered'] = True
                        save_alerts(alerts)
                    elif ema_50 < ema_200 and alert.get('cross_triggered', False):
                        alert['cross_triggered'] = False
                        save_alerts(alerts)
            
            if alert_triggered and not alert.get('triggered', False):
                triggered_alerts.append({
                    'id': alert['id'],
                    'type': alert['type'],
                    'current_price': current_price,
                    'reason': trigger_reason,
                    'details': trigger_details,
                    'alert': alert
                })
                alert['triggered'] = True
                alert['triggered_at'] = datetime.now().isoformat()
                save_alerts(alerts)
                print(f"Alert {alert['id']} triggered: {trigger_reason}")
            elif not alert_triggered:
                if alert.get('triggered', False):
                    alert['triggered'] = False
                    alert.pop('triggered_at', None)
                    save_alerts(alerts)
                    print(f"Alert {alert['id']} reset")
        
        return jsonify({
            'current_price': current_price,
            'current_volume': current_volume,
            'rsi': rsi,
            'ema_50': ema_50,
            'ema_200': ema_200,
            'volatility': volatility,
            'triggered_alerts': triggered_alerts
        })
    except Exception as e:
        print(f"Error checking alerts: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5601, debug=True)
